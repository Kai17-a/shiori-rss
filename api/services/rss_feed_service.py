import logging
import sqlite3
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET
from typing import cast
from time import mktime

import feedparser  # type: ignore
import httpx
from fastapi import HTTPException

from api.database import get_db
from api.model.models import (
    RSSFeedCreate,
    RSSFeedArticleListResponse,
    RSSFeedArticleResponse,
    RSSFeedExecuteResponse,
    RSSFeedListResponse,
    RSSFeedResponse,
    RSSFeedUpdate,
)
from api.repositories.rss_feed_repo import RSSFeedRepository
from api.repositories.settings_repo import SettingsRepository
from api.repositories.webhook_endpoint_repo import WebhookEndpointRepository
from api.services.webhook_service import (
    build_rss_notification_payload,
    detect_webhook_service,
    send_webhook,
)

logger = logging.getLogger(__name__)


class RSSFeedService:
    def _parse_article_published(self, value: object | None) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                try:
                    return parsedate_to_datetime(value)
                except (TypeError, ValueError):
                    return None
        return None

    def _extract_article_published(
        self, entry: feedparser.FeedParserDict | dict[str, object]
    ) -> datetime | None:
        pub_date = entry.get("pubDate")
        if pub_date is not None:
            parsed_pub_date = self._parse_article_published(pub_date)
            if parsed_pub_date is not None:
                return parsed_pub_date

        published = entry.get("published")
        if published is not None:
            parsed_published = self._parse_article_published(published)
            if parsed_published is not None:
                return parsed_published

        published_parsed = entry.get("published_parsed")
        if published_parsed is not None:
            return datetime.fromtimestamp(mktime(cast(tuple, published_parsed)))
        return None

    def _article_published_sort_key(self, row: dict) -> tuple[int, float, int]:
        published = self._parse_article_published(row.get("published"))
        if published is None:
            return (0, float("-inf"), int(row.get("id") or 0))
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        return (1, published.timestamp(), int(row.get("id") or 0))

    def _extract_webhook_error_detail(self, response: httpx.Response) -> str | None:
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                data = response.json()
            except ValueError:
                return None

            if isinstance(data, dict):
                for key in ("detail", "message", "error"):
                    value = data.get(key)
                    if value:
                        return str(value)
                return str(data)
            return str(data)

        try:
            text = response.text.strip()
        except Exception:
            return None

        return text or None

    def _raise_webhook_error(
        self, webhook_service: str, response: httpx.Response | None = None
    ) -> None:
        if response is not None:
            response_detail = self._extract_webhook_error_detail(response)
            if response_detail:
                logger.error(
                    "%s webhook notification failed: %s",
                    webhook_service.capitalize(),
                    response_detail,
                )
        raise HTTPException(
            status_code=502,
            detail="Failed to notify webhook",
        )

    def _parse_rss_feed(self, content: bytes) -> feedparser.FeedParserDict:
        parsed = feedparser.parse(content)
        if parsed.bozo:
            raise HTTPException(
                status_code=422, detail="RSS feed URL is not a valid RSS feed"
            )
        if not parsed.feed and not parsed.entries:
            raise HTTPException(
                status_code=422, detail="RSS feed URL is not a valid RSS feed"
            )
        return parsed

    def _get_feed_title(
        self, parsed_feed: feedparser.FeedParserDict, fallback_title: str
    ) -> str:
        feed_data = getattr(parsed_feed, "feed", None)
        if feed_data is None and isinstance(parsed_feed, dict):
            feed_data = parsed_feed.get("feed")
        if feed_data is None:
            return fallback_title
        if isinstance(feed_data, dict):
            return str(feed_data.get("title") or fallback_title)
        return str(getattr(feed_data, "title", None) or fallback_title)

    def _validate_rss_feed_url(self, url: str) -> None:
        try:
            response = httpx.get(url, timeout=5.0, follow_redirects=True)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=422, detail="RSS feed URL is not reachable"
            ) from exc

        if response.status_code >= 400:
            raise HTTPException(status_code=422, detail="RSS feed URL is not reachable")

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as exc:
            raise HTTPException(
                status_code=422, detail="RSS feed URL is not a valid RSS feed"
            ) from exc

        tag = root.tag.split("}", 1)[-1].lower()
        if tag == "rss":
            channel = root.find("channel")
            if channel is None:
                raise HTTPException(
                    status_code=422, detail="RSS feed URL is not a valid RSS feed"
                )
            return
        if tag == "feed":
            return

        raise HTTPException(
            status_code=422, detail="RSS feed URL is not a valid RSS feed"
        )

    def _chunk_embeds(
        self, embeds: list[dict[str, object]], chunk_size: int = 10
    ) -> list[list[dict[str, object]]]:
        return [
            embeds[index : index + chunk_size]
            for index in range(0, len(embeds), chunk_size)
        ]

    def _load_sent_article_urls(self, conn, feed_id: int) -> set[str]:
        rows = conn.execute(
            "SELECT url FROM rss_feed_articles WHERE feed_id = ?",
            (feed_id,),
        ).fetchall()
        return {str(row["url"]) for row in rows}

    def _record_articles(
        self, conn, feed_id: int, articles: list[dict[str, object]]
    ) -> None:
        has_published = RSSFeedRepository(conn)._has_column(
            "rss_feed_articles", "published"
        )
        has_notification_state = RSSFeedRepository(conn)._has_column(
            "rss_feed_articles", "webhook_notified"
        )
        insert_query = (
            """
                INSERT OR IGNORE INTO rss_feed_articles
                    (feed_id, url, title, summary, published, webhook_notified)
                VALUES (?, ?, ?, ?, ?, 0)
                """
            if has_published and has_notification_state
            else """
                INSERT OR IGNORE INTO rss_feed_articles (feed_id, url, title, published)
                VALUES (?, ?, ?, ?)
                """
            if has_published
            else """
                INSERT OR IGNORE INTO rss_feed_articles (feed_id, url, title)
                VALUES (?, ?, ?)
                """
        )
        for article in articles:
            published = article.get("published")
            published_value = (
                published.strftime("%Y-%m-%d %H:%M:%S")
                if isinstance(published, datetime)
                else published
            )
            params = (
                feed_id,
                article["url"],
                article.get("title"),
                article.get("summary"),
                published_value,
            )
            if has_published and has_notification_state:
                insert_params = params
            elif has_published:
                insert_params = (params[0], params[1], params[2], params[4])
            else:
                insert_params = params[:3]
            conn.execute(insert_query, insert_params)

    def _load_pending_articles(self, conn, feed_id: int) -> list[dict[str, object]]:
        rows = conn.execute(
            """
            SELECT url, title, summary, published
            FROM rss_feed_articles
            WHERE feed_id = ? AND webhook_notified = 0
            ORDER BY id ASC
            """,
            (feed_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _mark_articles_notified(
        self, conn, feed_id: int, articles: list[dict[str, object]]
    ) -> None:
        conn.executemany(
            """
            UPDATE rss_feed_articles SET webhook_notified = 1
            WHERE feed_id = ? AND url = ?
            """,
            [(feed_id, article["url"]) for article in articles],
        )

    def _verify_webhook_endpoints(self, conn, webhook_ids: list[int]) -> None:
        repo = WebhookEndpointRepository(conn)
        missing = [
            webhook_id
            for webhook_id in webhook_ids
            if repo.find_by_id(webhook_id) is None
        ]
        if missing:
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    def _sync_webhook_endpoints(
        self, repo: RSSFeedRepository, feed_id: int, webhook_ids: list[int] | None
    ) -> None:
        if webhook_ids is None:
            return
        unique_webhook_ids = list(dict.fromkeys(webhook_ids))
        self._verify_webhook_endpoints(repo.conn, unique_webhook_ids)
        repo.set_webhook_ids(feed_id, unique_webhook_ids)

    def create(self, data: RSSFeedCreate) -> RSSFeedResponse:
        with get_db() as conn:
            repo = RSSFeedRepository(conn)
            if repo.find_by_url(str(data.url)) is not None:
                raise HTTPException(
                    status_code=409, detail="RSS feed URL already exists"
                )
            self._validate_rss_feed_url(str(data.url))
            try:
                row = repo.insert(
                    str(data.url),
                    data.title,
                    data.description,
                    data.notify_webhook_enabled,
                )
            except sqlite3.IntegrityError:
                raise HTTPException(
                    status_code=409, detail="RSS feed URL already exists"
                )
            self._sync_webhook_endpoints(repo, row["id"], data.webhook_ids)
            saved_row = repo.find_by_id(row["id"])
            assert saved_row is not None
            return RSSFeedResponse(**saved_row)

    def list(
        self, q: str | None = None, page: int = 1, per_page: int = 20
    ) -> RSSFeedListResponse:
        with get_db() as conn:
            repo = RSSFeedRepository(conn)
            total = repo.count_all(q=q)
            total_pages = max((total + per_page - 1) // per_page, 1) if total else 0
            page = max(page, 1)
            if total_pages and page > total_pages:
                page = total_pages
            offset = (page - 1) * per_page
            rows = repo.find_all(q=q, limit=per_page, offset=offset)
            items = [RSSFeedResponse(**row) for row in rows]
            return RSSFeedListResponse(
                items=items,
                total=total,
                page=page,
                per_page=per_page,
                total_pages=total_pages,
            )

    def get(self, feed_id: int) -> RSSFeedResponse:
        with get_db() as conn:
            repo = RSSFeedRepository(conn)
            row = repo.find_by_id(feed_id)
            if row is None:
                raise HTTPException(status_code=404, detail="RSS feed not found")
            return RSSFeedResponse(**row)

    def list_articles(
        self,
        feed_id: int,
        q: str | None = None,
        page: int = 1,
        per_page: int = 20,
        published_from: str | None = None,
        published_to: str | None = None,
    ) -> RSSFeedArticleListResponse:
        with get_db() as conn:
            repo = RSSFeedRepository(conn)
            if repo.find_by_id(feed_id) is None:
                raise HTTPException(status_code=404, detail="RSS feed not found")
            rows = repo.find_articles_by_feed_id(feed_id)
            rows.sort(key=self._article_published_sort_key, reverse=True)
            if q is not None:
                query = q.strip().lower()
                if query:
                    rows = [
                        row
                        for row in rows
                        if query in str(row.get("title") or "").lower()
                    ]
            rows = [
                row
                for row in rows
                if self._article_matches_date_range(
                    row,
                    published_from=published_from,
                    published_to=published_to,
                )
            ]
            total = len(rows)
            total_pages = max((total + per_page - 1) // per_page, 1) if total else 0
            page = max(page, 1)
            if total_pages and page > total_pages:
                page = total_pages
            offset = (page - 1) * per_page
            rows = rows[offset : offset + per_page]
            items = [
                RSSFeedArticleResponse(
                    **{
                        **row,
                        "published": self._parse_article_published(
                            row.get("published")
                        ),
                    }
                )
                for row in rows
            ]
            return RSSFeedArticleListResponse(
                items=items,
                total=total,
                page=page,
                per_page=per_page,
                total_pages=total_pages,
            )

    def _article_matches_date_range(
        self,
        row: dict,
        published_from: str | None = None,
        published_to: str | None = None,
    ) -> bool:
        published = row.get("published") or row.get("created_at")
        if not isinstance(published, str):
            return False
        published_date = published[:10]
        if published_from is not None and published_date < published_from:
            return False
        if published_to is not None and published_date > published_to:
            return False
        return True

    def update(self, feed_id: int, data: RSSFeedUpdate) -> RSSFeedResponse:
        with get_db() as conn:
            repo = RSSFeedRepository(conn)
            if repo.find_by_id(feed_id) is None:
                raise HTTPException(status_code=404, detail="RSS feed not found")
            payload = data.model_dump(exclude_unset=True)
            fields: dict[str, object] = {}
            if "url" in payload and payload["url"] is not None:
                url = str(payload["url"])
                existing = repo.find_by_url(url)
                if existing is not None and existing["id"] != feed_id:
                    raise HTTPException(
                        status_code=409, detail="RSS feed URL already exists"
                    )
                self._validate_rss_feed_url(url)
                fields["url"] = url
            if "title" in payload and payload["title"] is not None:
                fields["title"] = payload["title"]
            if "description" in payload:
                fields["description"] = payload["description"]
            if (
                "notify_webhook_enabled" in payload
                and payload["notify_webhook_enabled"] is not None
            ):
                fields["notify_webhook_enabled"] = int(
                    payload["notify_webhook_enabled"]
                )
            if "webhook_ids" in payload:
                self._sync_webhook_endpoints(repo, feed_id, payload["webhook_ids"])
            row = repo.update(feed_id, fields)
            assert row is not None
            return RSSFeedResponse(**row)

    def delete(self, feed_id: int) -> None:
        with get_db() as conn:
            repo = RSSFeedRepository(conn)
            if not repo.delete(feed_id):
                raise HTTPException(status_code=404, detail="RSS feed not found")

    def execute(self, feed_id: int) -> RSSFeedExecuteResponse:
        with get_db() as conn:
            repo = RSSFeedRepository(conn)
            row = repo.find_by_id(feed_id)
            if row is None:
                raise HTTPException(status_code=404, detail="RSS feed not found")
            webhook_rows = WebhookEndpointRepository(conn).find_enabled()
            selected_webhook_ids = set(repo.find_webhook_ids(feed_id))
            if selected_webhook_ids:
                webhook_rows = [
                    entry
                    for entry in webhook_rows
                    if int(entry["id"]) in selected_webhook_ids
                ]
            webhook_urls = [str(entry["url"]) for entry in webhook_rows]
            include_summary = SettingsRepository(conn).get_bool(
                "webhook_include_summary_enabled", default=True
            )
            try:
                response = httpx.get(row["url"], timeout=5.0, follow_redirects=True)
            except httpx.HTTPError as exc:
                raise HTTPException(
                    status_code=422, detail="RSS feed URL is not reachable"
                ) from exc

            if response.status_code >= 400:
                raise HTTPException(
                    status_code=422, detail="RSS feed URL is not reachable"
                )

            parsed_feed = self._parse_rss_feed(response.content)
            feed_title = self._get_feed_title(parsed_feed, str(row["title"]))
            sent_urls = self._load_sent_article_urls(conn, feed_id)
            articles: list[dict[str, object]] = []
            for entry in parsed_feed.entries:
                entry_link = entry.get("link")
                if not entry_link or entry_link in sent_urls:
                    continue
                summary = entry.get("summary") or entry.get("description")
                articles.append(
                    {
                        "url": entry_link,
                        "title": entry.get("title") or "(no title)",
                        "summary": summary,
                        "published": self._extract_article_published(entry),
                    }
                )

            self._record_articles(conn, feed_id, articles)
            # Fetch persistence must survive a later webhook failure so pending
            # articles can be delivered by a future execution.
            conn.commit()
            pending_articles = self._load_pending_articles(conn, feed_id)

            if not webhook_urls:
                return RSSFeedExecuteResponse(
                    feed_id=feed_id,
                    title=row["title"],
                    delivered=False,
                    delivered_count=0,
                    message=(
                        f"Saved {len(articles)} new article(s) without webhook notification."
                        if articles
                        else "No new articles found. Pending articles remain unnotified."
                    ),
                )

            if not pending_articles:
                return RSSFeedExecuteResponse(
                    feed_id=feed_id,
                    title=row["title"],
                    delivered=True,
                    delivered_count=0,
                    message="No new articles found.",
                )

            article_chunks = self._chunk_embeds(pending_articles) or [[]]
            delivered_count = 0
            last_failed_service: str | None = None
            last_failed_response: httpx.Response | None = None
            for webhook_url in webhook_urls:
                webhook_service = detect_webhook_service(webhook_url)
                delivered = True
                try:
                    for index, chunk in enumerate(article_chunks, start=1):
                        payload = build_rss_notification_payload(
                            webhook_service,
                            feed_title=feed_title,
                            articles=chunk,
                            total_articles=len(pending_articles),
                            chunk_index=index,
                            chunk_count=len(article_chunks),
                            include_summary=include_summary,
                        )
                        response = send_webhook(webhook_url, payload)
                        if response.status_code >= 400:
                            last_failed_response = response
                            delivered = False
                            break
                except httpx.HTTPError:
                    last_failed_response = None
                    delivered = False

                if delivered:
                    delivered_count += 1
                else:
                    last_failed_service = webhook_service

            if delivered_count == 0:
                self._raise_webhook_error(
                    last_failed_service or "webhook", last_failed_response
                )

            self._mark_articles_notified(conn, feed_id, pending_articles)

            return RSSFeedExecuteResponse(
                feed_id=feed_id,
                title=row["title"],
                delivered=True,
                delivered_count=delivered_count,
                message=f"Posted {len(pending_articles)} pending article(s).",
            )
