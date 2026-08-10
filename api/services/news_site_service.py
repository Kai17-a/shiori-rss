from __future__ import annotations

import json
import logging
import re
import sqlite3
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

from api.database import get_db
from api.model.models import (
    NewsSiteArticleListResponse,
    NewsSiteArticleResponse,
    NewsSiteCreate,
    NewsSiteExecuteResponse,
    NewsSiteListResponse,
    NewsSiteResponse,
    NewsSiteUpdate,
)
from api.repositories.news_site_repo import NewsSiteRepository
from api.repositories.settings_repo import SettingsRepository
from api.repositories.webhook_endpoint_repo import WebhookEndpointRepository
from api.services.llm_service import (
    analyze_news_page,
    load_llm_config,
    new_diagnostic_reference,
)
from api.services.webhook_service import (
    build_rss_notification_payload,
    detect_webhook_service,
    send_webhook,
)

logger = logging.getLogger(__name__)

MAX_ARTICLES_PER_RUN = 100
LOG_PREVIEW_CHARS = 300


def _safe_target_url(value: str) -> str:
    parsed = urlparse(value)
    hostname = parsed.hostname or "unknown-host"
    try:
        port = f":{parsed.port}" if parsed.port else ""
    except ValueError:
        port = ""
    return f"{parsed.scheme}://{hostname}{port}{parsed.path}"


def _response_preview(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()[:LOG_PREVIEW_CHARS]


def _read_element_value(element, selector: object, attribute: object) -> str | None:
    if not isinstance(selector, str) or not selector:
        return None
    selected = element.select_one(selector)
    if selected is None:
        return None
    if isinstance(attribute, str) and attribute:
        value = selected.get(attribute)
        return str(value).strip() if value is not None else None
    value = selected.get_text(" ", strip=True)
    return value or None


def _normalize_published(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    normalized = candidate.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).isoformat(sep=" ")
    except ValueError:
        try:
            return datetime.strptime(candidate, "%Y.%m.%d").isoformat(sep=" ")
        except ValueError:
            pass
        try:
            return parsedate_to_datetime(candidate).isoformat(sep=" ")
        except (TypeError, ValueError, OverflowError):
            return None


def extract_news_articles(
    *,
    html: str,
    page_url: str,
    scrape_config: dict[str, object],
    reference_id: str | None = None,
) -> list[dict[str, object]]:
    """Extract normalized articles from HTML using a validated LLM recipe."""
    soup = BeautifulSoup(html, "html.parser")
    try:
        items = soup.select(str(scrape_config["item_selector"]))
    except Exception as exc:
        logger.error(
            "news_selector_invalid reference_id=%s target_url=%s item_selector=%r",
            reference_id or "none",
            _safe_target_url(page_url),
            scrape_config.get("item_selector"),
            exc_info=True,
        )
        reference = f" Reference ID: {reference_id}." if reference_id else ""
        raise HTTPException(
            status_code=422,
            detail=f"Selector validation error: The LLM generated invalid CSS.{reference}",
        ) from exc

    articles: list[dict[str, object]] = []
    seen_urls: set[str] = set()
    for item in items:
        try:
            title = _read_element_value(
                item, str(scrape_config["title_selector"]), None
            )
            link = _read_element_value(
                item,
                str(scrape_config["link_selector"]),
                str(scrape_config["link_attribute"]),
            )
            published = _read_element_value(
                item,
                scrape_config.get("published_selector"),
                scrape_config.get("published_attribute"),
            )
            summary = _read_element_value(
                item, scrape_config.get("summary_selector"), None
            )
        except Exception as exc:
            logger.error(
                "news_selector_invalid reference_id=%s target_url=%s item_selector=%r",
                reference_id or "none",
                _safe_target_url(page_url),
                scrape_config.get("item_selector"),
                exc_info=True,
            )
            reference = f" Reference ID: {reference_id}." if reference_id else ""
            raise HTTPException(
                status_code=422,
                detail=f"Selector validation error: The LLM generated invalid CSS.{reference}",
            ) from exc

        if not title or not link:
            continue
        article_url = urljoin(page_url, link)
        parsed = urlparse(article_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        if article_url in seen_urls:
            continue
        seen_urls.add(article_url)
        articles.append(
            {
                "url": article_url,
                "title": title,
                "summary": summary,
                "published": _normalize_published(published),
            }
        )
        if len(articles) >= MAX_ARTICLES_PER_RUN:
            break
    return articles


def _selector_diagnostics(
    html: str, scrape_config: dict[str, object]
) -> dict[str, object]:
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(str(scrape_config["item_selector"]))
    title_matches = 0
    link_matches = 0
    for item in items:
        if _read_element_value(item, scrape_config.get("title_selector"), None):
            title_matches += 1
        if _read_element_value(
            item,
            scrape_config.get("link_selector"),
            scrape_config.get("link_attribute"),
        ):
            link_matches += 1
    return {
        "previous_scrape_config": scrape_config,
        "item_matches": len(items),
        "title_matches": title_matches,
        "link_matches": link_matches,
    }


def _selector_signature(scrape_config: dict[str, object]) -> tuple[object, ...]:
    return tuple(
        scrape_config.get(key)
        for key in (
            "item_selector",
            "title_selector",
            "link_selector",
            "link_attribute",
            "published_selector",
            "published_attribute",
            "summary_selector",
        )
    )


class NewsSiteService:
    def _fetch_page(self, url: str, *, reference_id: str | None = None) -> str:
        reference_id = reference_id or new_diagnostic_reference()
        try:
            response = httpx.get(url, timeout=15.0, follow_redirects=True)
        except httpx.HTTPError as exc:
            logger.error(
                "news_site_fetch_failed reference_id=%s target_url=%s exception=%s",
                reference_id,
                _safe_target_url(url),
                type(exc).__name__,
            )
            raise HTTPException(
                status_code=422,
                detail=(
                    "Target-site fetch error: Shiori Feed could not connect to the target "
                    "news site. "
                    f"This failed before LLM analysis. Reference ID: {reference_id}."
                ),
            ) from exc
        if response.status_code >= 400:
            logger.error(
                "news_site_fetch_rejected reference_id=%s target_url=%s upstream_status=%s "
                "upstream_server=%r response_preview=%r",
                reference_id,
                _safe_target_url(url),
                response.status_code,
                response.headers.get("server"),
                _response_preview(response.text),
            )
            if response.status_code in {401, 403}:
                reason = (
                    "The site may require authentication or block automated requests."
                )
            elif response.status_code == 429:
                reason = "The site is rate-limiting automated requests."
            else:
                reason = "The target page could not be downloaded."
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Target-site fetch error: The site returned HTTP {response.status_code} "
                    f"before LLM analysis. {reason} Reference ID: {reference_id}."
                ),
            )
        if not response.text.strip():
            logger.error(
                "news_site_fetch_empty reference_id=%s target_url=%s",
                reference_id,
                _safe_target_url(url),
            )
            raise HTTPException(
                status_code=422,
                detail=(
                    "Target-site fetch error: The site returned empty HTML before LLM analysis. "
                    f"Reference ID: {reference_id}."
                ),
            )
        return response.text

    def _analyze_and_test(
        self, url: str
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        reference_id = new_diagnostic_reference()
        with get_db() as conn:
            llm_config = load_llm_config(SettingsRepository(conn))
        if llm_config is None:
            raise HTTPException(
                status_code=400,
                detail="LLM settings must be configured before registering a news site",
            )
        html = self._fetch_page(url, reference_id=reference_id)
        scrape_config = analyze_news_page(
            llm_config,
            page_url=url,
            html=html,
            reference_id=reference_id,
        )
        articles = extract_news_articles(
            html=html,
            page_url=url,
            scrape_config=scrape_config,
            reference_id=reference_id,
        )
        if not articles:
            diagnostics = _selector_diagnostics(html, scrape_config)
            logger.warning(
                "news_extraction_retry reference_id=%s provider=%s model=%s target_url=%s "
                "item_selector=%r title_selector=%r link_selector=%r "
                "item_matches=%s title_matches=%s link_matches=%s",
                reference_id,
                llm_config.provider,
                llm_config.model,
                _safe_target_url(url),
                scrape_config.get("item_selector"),
                scrape_config.get("title_selector"),
                scrape_config.get("link_selector"),
                diagnostics["item_matches"],
                diagnostics["title_matches"],
                diagnostics["link_matches"],
            )
            retry_config = analyze_news_page(
                llm_config,
                page_url=url,
                html=html,
                reference_id=reference_id,
                retry_context=diagnostics,
            )
            if _selector_signature(retry_config) == _selector_signature(scrape_config):
                logger.error(
                    "news_extraction_retry_unchanged reference_id=%s provider=%s model=%s "
                    "target_url=%s",
                    reference_id,
                    llm_config.provider,
                    llm_config.model,
                    _safe_target_url(url),
                )
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Selector extraction error: The target site and LLM request "
                        "succeeded, but the generated selectors did not extract any "
                        "article titles and links. The automatic retry returned the same "
                        f"selectors. Reference ID: {reference_id}."
                    ),
                )
            retry_articles = extract_news_articles(
                html=html,
                page_url=url,
                scrape_config=retry_config,
                reference_id=reference_id,
            )
            if retry_articles:
                logger.info(
                    "news_extraction_retry_succeeded reference_id=%s provider=%s model=%s "
                    "target_url=%s article_count=%s",
                    reference_id,
                    llm_config.provider,
                    llm_config.model,
                    _safe_target_url(url),
                    len(retry_articles),
                )
                return retry_config, retry_articles
            retry_diagnostics = _selector_diagnostics(html, retry_config)
            logger.error(
                "news_extraction_empty reference_id=%s provider=%s model=%s target_url=%s "
                "item_selector=%r title_selector=%r link_selector=%r "
                "item_matches=%s title_matches=%s link_matches=%s",
                reference_id,
                llm_config.provider,
                llm_config.model,
                _safe_target_url(url),
                retry_config.get("item_selector"),
                retry_config.get("title_selector"),
                retry_config.get("link_selector"),
                retry_diagnostics["item_matches"],
                retry_diagnostics["title_matches"],
                retry_diagnostics["link_matches"],
            )
            raise HTTPException(
                status_code=422,
                detail=(
                    "Selector extraction error: The target site and LLM request succeeded, "
                    "but the generated selectors "
                    "did not extract any article titles and links. The automatic selector "
                    f"retry also failed. Reference ID: {reference_id}."
                ),
            )
        return scrape_config, articles

    def _verify_webhooks(self, conn, webhook_ids: list[int]) -> None:
        repo = WebhookEndpointRepository(conn)
        if any(repo.find_by_id(webhook_id) is None for webhook_id in webhook_ids):
            raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    def _sync_webhooks(
        self, repo: NewsSiteRepository, site_id: int, webhook_ids: list[int] | None
    ) -> None:
        if webhook_ids is None:
            return
        self._verify_webhooks(repo.conn, webhook_ids)
        repo.set_webhook_ids(site_id, webhook_ids)

    def _to_response(self, row: dict) -> NewsSiteResponse:
        response_row = {
            key: value for key, value in row.items() if key != "scrape_config"
        }
        return NewsSiteResponse(**response_row)

    def create(self, data: NewsSiteCreate) -> NewsSiteResponse:
        url = str(data.url)
        with get_db() as conn:
            repo = NewsSiteRepository(conn)
            if repo.find_by_url(url) is not None:
                raise HTTPException(
                    status_code=409, detail="News site URL already exists"
                )
            if data.webhook_ids is not None:
                self._verify_webhooks(conn, data.webhook_ids)

        scrape_config, _ = self._analyze_and_test(url)
        title = data.title or str(scrape_config["site_title"])
        with get_db() as conn:
            repo = NewsSiteRepository(conn)
            try:
                row = repo.insert(
                    url=url,
                    title=title,
                    description=data.description,
                    scrape_config=json.dumps(scrape_config, ensure_ascii=False),
                    icon_url=str(data.icon_url) if data.icon_url else None,
                )
            except sqlite3.IntegrityError as exc:
                raise HTTPException(
                    status_code=409, detail="News site URL already exists"
                ) from exc
            self._sync_webhooks(repo, int(row["id"]), data.webhook_ids)
            saved = repo.find_by_id(int(row["id"]))
            assert saved is not None
            return self._to_response(saved)

    def list(
        self, *, q: str | None = None, page: int = 1, per_page: int = 20
    ) -> NewsSiteListResponse:
        with get_db() as conn:
            repo = NewsSiteRepository(conn)
            total = repo.count_all(q)
            total_pages = (total + per_page - 1) // per_page if total else 0
            if total_pages and page > total_pages:
                page = total_pages
            rows = repo.find_all(q, per_page, (page - 1) * per_page)
            return NewsSiteListResponse(
                items=[self._to_response(row) for row in rows],
                total=total,
                page=page,
                per_page=per_page,
                total_pages=total_pages,
            )

    def get(self, site_id: int) -> NewsSiteResponse:
        with get_db() as conn:
            row = NewsSiteRepository(conn).find_by_id(site_id)
            if row is None:
                raise HTTPException(status_code=404, detail="News site not found")
            return self._to_response(row)

    def update(self, site_id: int, data: NewsSiteUpdate) -> NewsSiteResponse:
        with get_db() as conn:
            repo = NewsSiteRepository(conn)
            current = repo.find_by_id(site_id)
            if current is None:
                raise HTTPException(status_code=404, detail="News site not found")

        payload = data.model_dump(exclude_unset=True)
        reanalyze = bool(payload.pop("reanalyze", False))
        fields: dict[str, object] = {}
        url = str(payload["url"]) if "url" in payload else str(current["url"])
        url_changed = url != current["url"]
        if url_changed:
            with get_db() as conn:
                existing = NewsSiteRepository(conn).find_by_url(url)
            if existing is not None and int(existing["id"]) != site_id:
                raise HTTPException(
                    status_code=409, detail="News site URL already exists"
                )
            fields["url"] = url
        if url_changed or reanalyze:
            scrape_config, _ = self._analyze_and_test(url)
            fields["scrape_config"] = json.dumps(scrape_config, ensure_ascii=False)
        if "title" in payload:
            fields["title"] = payload["title"]
        if "description" in payload:
            fields["description"] = payload["description"]
        if "notify_webhook_enabled" in payload:
            fields["notify_webhook_enabled"] = int(payload["notify_webhook_enabled"])
        if "icon_url" in payload:
            fields["icon_url"] = (
                str(payload["icon_url"]) if payload["icon_url"] else None
            )
            fields["icon_data"] = None
            fields["icon_media_type"] = None

        with get_db() as conn:
            repo = NewsSiteRepository(conn)
            if "webhook_ids" in payload:
                self._sync_webhooks(repo, site_id, payload["webhook_ids"])
            try:
                row = repo.update(site_id, fields)
            except sqlite3.IntegrityError as exc:
                raise HTTPException(
                    status_code=409, detail="News site URL already exists"
                ) from exc
            assert row is not None
            return self._to_response(row)

    def set_icon(
        self, site_id: int, *, content: bytes, media_type: str, public_url: str
    ) -> NewsSiteResponse:
        from api.services.rss_feed_service import (
            ALLOWED_ICON_MEDIA_TYPES,
            MAX_ICON_BYTES,
        )

        if media_type not in ALLOWED_ICON_MEDIA_TYPES:
            raise HTTPException(
                status_code=422, detail="Icon must be PNG, JPEG, GIF, or WebP"
            )
        if not content or len(content) > MAX_ICON_BYTES:
            raise HTTPException(
                status_code=422, detail="Icon must be between 1 byte and 1 MB"
            )
        with get_db() as conn:
            repo = NewsSiteRepository(conn)
            row = repo.update(
                site_id,
                {
                    "icon_url": public_url,
                    "icon_data": content,
                    "icon_media_type": media_type,
                },
            )
            if row is None:
                raise HTTPException(status_code=404, detail="News site not found")
            return self._to_response(row)

    def get_icon(self, site_id: int) -> tuple[bytes, str]:
        with get_db() as conn:
            icon = NewsSiteRepository(conn).find_icon(site_id)
            if icon is None:
                raise HTTPException(status_code=404, detail="News site icon not found")
            return icon

    def clear_icon(self, site_id: int) -> NewsSiteResponse:
        with get_db() as conn:
            repo = NewsSiteRepository(conn)
            row = repo.update(
                site_id,
                {
                    "icon_url": None,
                    "icon_data": None,
                    "icon_media_type": None,
                },
            )
            if row is None:
                raise HTTPException(status_code=404, detail="News site not found")
            return self._to_response(row)

    def delete(self, site_id: int) -> None:
        with get_db() as conn:
            if not NewsSiteRepository(conn).delete(site_id):
                raise HTTPException(status_code=404, detail="News site not found")

    def list_articles(
        self,
        site_id: int,
        *,
        q: str | None = None,
        page: int = 1,
        per_page: int = 20,
        published_from: str | None = None,
        published_to: str | None = None,
    ) -> NewsSiteArticleListResponse:
        with get_db() as conn:
            repo = NewsSiteRepository(conn)
            if repo.find_by_id(site_id) is None:
                raise HTTPException(status_code=404, detail="News site not found")
            total = repo.count_articles(
                site_id,
                q=q,
                published_from=published_from,
                published_to=published_to,
            )
            total_pages = (total + per_page - 1) // per_page if total else 0
            if total_pages and page > total_pages:
                page = total_pages
            rows = repo.find_articles(
                site_id,
                q=q,
                published_from=published_from,
                published_to=published_to,
                limit=per_page,
                offset=(page - 1) * per_page,
            )
            items = []
            for row in rows:
                published = row.get("published")
                normalized_published = (
                    _normalize_published(published)
                    if isinstance(published, str)
                    else published
                )
                if published and normalized_published is None:
                    logger.warning(
                        "news_article_published_invalid site_id=%s article_id=%s value=%r",
                        site_id,
                        row.get("id"),
                        published,
                    )
                items.append(
                    NewsSiteArticleResponse(
                        **{**row, "published": normalized_published}
                    )
                )
            return NewsSiteArticleListResponse(
                items=items,
                total=total,
                page=page,
                per_page=per_page,
                total_pages=total_pages,
            )

    def execute(self, site_id: int) -> NewsSiteExecuteResponse:
        with get_db() as conn:
            repo = NewsSiteRepository(conn)
            row = repo.find_by_id(site_id)
            if row is None:
                raise HTTPException(status_code=404, detail="News site not found")
            webhook_rows = WebhookEndpointRepository(conn).find_enabled()
            selected = set(repo.find_webhook_ids(site_id))
            if selected:
                webhook_rows = [
                    webhook
                    for webhook in webhook_rows
                    if int(webhook["id"]) in selected
                ]
            sent_urls = repo.load_sent_article_urls(site_id)
            include_summary = SettingsRepository(conn).get_bool(
                "webhook_include_summary_enabled", default=True
            )

        html = self._fetch_page(str(row["url"]))
        try:
            scrape_config = json.loads(str(row["scrape_config"]))
        except ValueError as exc:
            raise HTTPException(
                status_code=500, detail="Stored scraping configuration is invalid"
            ) from exc
        articles = [
            article
            for article in extract_news_articles(
                html=html, page_url=str(row["url"]), scrape_config=scrape_config
            )
            if str(article["url"]) not in sent_urls
        ]
        with get_db() as conn:
            repo = NewsSiteRepository(conn)
            repo.record_articles(site_id, articles)
            conn.commit()
            pending_articles = repo.find_pending_articles(site_id)

        if not webhook_rows:
            return NewsSiteExecuteResponse(
                site_id=site_id,
                title=str(row["title"]),
                delivered=False,
                delivered_count=0,
                message=(
                    f"Saved {len(articles)} new article(s) without webhook notification."
                    if articles
                    else "No new articles found. Pending articles remain unnotified."
                ),
            )

        if not pending_articles:
            return NewsSiteExecuteResponse(
                site_id=site_id,
                title=str(row["title"]),
                delivered=True,
                delivered_count=0,
                message="No new articles found.",
            )

        chunks = [
            pending_articles[index : index + 10]
            for index in range(0, len(pending_articles), 10)
        ]
        delivered_count = 0
        for webhook in webhook_rows:
            webhook_url = str(webhook["url"])
            service = detect_webhook_service(webhook_url)
            delivered = True
            try:
                for index, chunk in enumerate(chunks, start=1):
                    response = send_webhook(
                        webhook_url,
                        build_rss_notification_payload(
                            service,
                            feed_title=str(row["title"]),
                            articles=chunk,
                            total_articles=len(pending_articles),
                            chunk_index=index,
                            chunk_count=len(chunks),
                            include_summary=include_summary,
                            icon_url=str(row["icon_url"])
                            if row.get("icon_url")
                            else None,
                        ),
                    )
                    if response.status_code >= 400:
                        delivered = False
                        break
            except httpx.HTTPError:
                delivered = False
            if delivered:
                delivered_count += 1

        if delivered_count == 0:
            raise HTTPException(status_code=502, detail="Failed to notify webhook")

        with get_db() as conn:
            NewsSiteRepository(conn).mark_articles_notified(site_id, pending_articles)
        return NewsSiteExecuteResponse(
            site_id=site_id,
            title=str(row["title"]),
            delivered=True,
            delivered_count=delivered_count,
            message=f"Posted {len(pending_articles)} pending article(s).",
        )
