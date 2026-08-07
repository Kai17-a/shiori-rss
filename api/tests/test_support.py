from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.parse import parse_qs, urlparse

from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request

from api.database import initialize_database
from api.model.models import (
    BookmarkCreate,
    BookmarkFavoriteUpdate,
    BookmarkUpdate,
    FolderCreate,
    FolderUpdate,
    LLMSettingsTestRequest,
    LLMSettingsUpdate,
    NewsSiteCreate,
    NewsSiteUpdate,
    RSSFeedCreate,
    RSSFeedUpdate,
    SettingsRssExecutionUpdate,
    SettingsRssWebhookNotificationUpdate,
    SettingsWebhookSummaryUpdate,
    SettingsWebhookCreate,
    SettingsWebhookPingRequest,
    SettingsWebhookUpdate,
    TagAttach,
    TagCreate,
    TagUpdate,
)
from api.services.bookmark_service import BookmarkService
from api.services.dashboard_service import DashboardService
from api.services.folder_service import FolderService
from api.services.news_site_service import NewsSiteService
from api.services.rss_feed_service import RSSFeedService
from api.services.settings_service import SettingsService
from api.services.tag_service import TagService


def build_test_db(db_path: str) -> None:
    initialize_database(db_path)


@dataclass
class Response:
    status_code: int
    payload: object | None = None

    def json(self):
        return self.payload

    @property
    def text(self):
        return "" if self.payload is None else str(self.payload)


class BookmarkListPayload:
    def __init__(self, payload: dict):
        self._payload = payload

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._payload[key]
        return self._payload["items"][key]

    def __iter__(self):
        return iter(self._payload["items"])

    def __len__(self):
        return len(self._payload["items"])


class CompatTestClient:
    __test__ = False

    def __init__(self, app, **kwargs):
        self.app = app
        self.base_url = kwargs.get("base_url", "http://testserver")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def _ok(self, payload=None, status_code=200):
        return Response(status_code=status_code, payload=payload)

    def _error(self, status_code: int, detail):
        return Response(status_code=status_code, payload={"detail": detail})

    def _parse(self, url: str) -> tuple[str, dict[str, list[str]]]:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        return parsed.path, query

    def _serialize(self, items):
        return [item.model_dump() for item in items]

    def _handle_folders(self, method: str, path: str, json):
        if method == "POST" and path == "/folders":
            body = FolderCreate(**(json or {}))
            payload = FolderService().create(body).model_dump()
            return self._ok(payload, 201)
        if method == "GET" and path == "/folders":
            return self._ok(self._serialize(FolderService().list()), 200)
        if method == "PATCH" and path.startswith("/folders/"):
            body = FolderUpdate(**(json or {}))
            payload = (
                FolderService().update(int(path.rsplit("/", 1)[1]), body).model_dump()
            )
            return self._ok(payload, 200)
        if method == "DELETE" and path.startswith("/folders/"):
            FolderService().delete(int(path.rsplit("/", 1)[1]))
            return self._ok(status_code=204)
        return None

    def _handle_tags(self, method: str, path: str, json):
        if method == "POST" and path == "/tags":
            body = TagCreate(**(json or {}))
            payload = TagService().create(body).model_dump()
            return self._ok(payload, 201)
        if method == "GET" and path == "/tags":
            return self._ok(self._serialize(TagService().list()), 200)
        if method == "PATCH" and path.startswith("/tags/"):
            body = TagUpdate(**(json or {}))
            payload = (
                TagService().update(int(path.rsplit("/", 1)[1]), body).model_dump()
            )
            return self._ok(payload, 200)
        if method == "DELETE" and path.startswith("/tags/"):
            TagService().delete(int(path.rsplit("/", 1)[1]))
            return self._ok(status_code=204)
        return None

    def _handle_rss_feeds(self, method: str, path: str, query, json):
        if method == "POST" and path == "/rss-feeds":
            body = RSSFeedCreate(**(json or {}))
            payload = RSSFeedService().create(body).model_dump()
            return self._ok(payload, 201)
        if method == "GET" and path == "/rss-feeds":
            q = query.get("q", [None])[0]
            page = int(query.get("page", ["1"])[0])
            per_page = int(query.get("per_page", ["20"])[0])
            payload = (
                RSSFeedService().list(q=q, page=page, per_page=per_page).model_dump()
            )
            return self._ok(payload, 200)
        if (
            method == "GET"
            and path.startswith("/rss-feeds/")
            and path.endswith("/articles")
        ):
            parts = path.strip("/").split("/")
            feed_id = int(parts[1])
            q = query.get("q", [None])[0]
            page = int(query.get("page", ["1"])[0])
            per_page = int(query.get("per_page", ["20"])[0])
            published_from = query.get("published_from", [None])[0]
            published_to = query.get("published_to", [None])[0]
            payload = (
                RSSFeedService()
                .list_articles(
                    feed_id,
                    q=q,
                    page=page,
                    per_page=per_page,
                    published_from=published_from,
                    published_to=published_to,
                )
                .model_dump()
            )
            return self._ok(payload, 200)
        if method == "GET" and path.startswith("/rss-feeds/"):
            payload = RSSFeedService().get(int(path.rsplit("/", 1)[1])).model_dump()
            return self._ok(payload, 200)
        if (
            method == "POST"
            and path.startswith("/rss-feeds/")
            and path.endswith("/execute")
        ):
            feed_id = int(path.split("/")[2])
            payload = RSSFeedService().execute(feed_id).model_dump()
            return self._ok(payload, 200)
        if method == "PATCH" and path.startswith("/rss-feeds/"):
            body = RSSFeedUpdate(**(json or {}))
            payload = (
                RSSFeedService().update(int(path.rsplit("/", 1)[1]), body).model_dump()
            )
            return self._ok(payload, 200)
        if method == "DELETE" and path.startswith("/rss-feeds/"):
            RSSFeedService().delete(int(path.rsplit("/", 1)[1]))
            return self._ok(status_code=204)
        return None

    def _handle_news_sites(self, method: str, path: str, query, json):
        if method == "POST" and path == "/news-sites":
            body = NewsSiteCreate(**(json or {}))
            return self._ok(NewsSiteService().create(body).model_dump(), 201)
        if method == "GET" and path == "/news-sites":
            payload = (
                NewsSiteService()
                .list(
                    q=query.get("q", [None])[0],
                    page=int(query.get("page", ["1"])[0]),
                    per_page=int(query.get("per_page", ["20"])[0]),
                )
                .model_dump()
            )
            return self._ok(payload, 200)
        if (
            method == "GET"
            and path.startswith("/news-sites/")
            and path.endswith("/articles")
        ):
            site_id = int(path.strip("/").split("/")[1])
            payload = (
                NewsSiteService()
                .list_articles(
                    site_id,
                    q=query.get("q", [None])[0],
                    page=int(query.get("page", ["1"])[0]),
                    per_page=int(query.get("per_page", ["20"])[0]),
                    published_from=query.get("published_from", [None])[0],
                    published_to=query.get("published_to", [None])[0],
                )
                .model_dump()
            )
            return self._ok(payload, 200)
        if (
            method == "POST"
            and path.startswith("/news-sites/")
            and path.endswith("/execute")
        ):
            site_id = int(path.strip("/").split("/")[1])
            return self._ok(NewsSiteService().execute(site_id).model_dump(), 200)
        if method == "GET" and path.startswith("/news-sites/"):
            site_id = int(path.rsplit("/", 1)[1])
            return self._ok(NewsSiteService().get(site_id).model_dump(), 200)
        if method == "PATCH" and path.startswith("/news-sites/"):
            site_id = int(path.rsplit("/", 1)[1])
            body = NewsSiteUpdate(**(json or {}))
            return self._ok(NewsSiteService().update(site_id, body).model_dump(), 200)
        if method == "DELETE" and path.startswith("/news-sites/"):
            NewsSiteService().delete(int(path.rsplit("/", 1)[1]))
            return self._ok(status_code=204)
        return None

    def _handle_bookmarks(self, method: str, path: str, query, json):
        if method == "POST" and path == "/bookmarks":
            body = BookmarkCreate(**(json or {}))
            payload = BookmarkService().create(body).model_dump()
            return self._ok(payload, 201)
        if method == "GET" and path == "/bookmarks":
            folder_id = int(query["folder_id"][0]) if "folder_id" in query else None
            tag_id = int(query["tag_id"][0]) if "tag_id" in query else None
            q = query["q"][0] if "q" in query else None
            is_favorite = (
                query["is_favorite"][0].lower() == "true"
                if "is_favorite" in query
                else None
            )
            sort = query.get("sort")
            page = int(query.get("page", ["1"])[0])
            per_page = int(query.get("per_page", ["20"])[0])
            payload = (
                BookmarkService()
                .list(
                    folder_id,
                    tag_id,
                    q,
                    is_favorite=is_favorite,
                    sort=sort,
                    page=page,
                    per_page=per_page,
                )
                .model_dump()
            )
            return self._ok(BookmarkListPayload(payload), 200)
        if method == "GET" and path.startswith("/bookmarks/") and "/tags" not in path:
            payload = BookmarkService().get(int(path.rsplit("/", 1)[1])).model_dump()
            return self._ok(payload, 200)
        if method == "PATCH" and path == "/bookmarks/favorite":
            body = BookmarkFavoriteUpdate(**(json or {}))
            payload = BookmarkService().set_favorite(body).model_dump()
            return self._ok(payload, 200)
        if method == "PATCH" and path == "/bookmarks/by-url" and "url" in query:
            body = BookmarkUpdate(**(json or {}))
            payload = (
                BookmarkService().update_by_url(query["url"][0], body).model_dump()
            )
            return self._ok(payload, 200)
        if method == "PATCH" and path.startswith("/bookmarks/") and "/tags" not in path:
            body = BookmarkUpdate(**(json or {}))
            payload = (
                BookmarkService().update(int(path.rsplit("/", 1)[1]), body).model_dump()
            )
            return self._ok(payload, 200)
        if method == "DELETE" and path == "/bookmarks":
            bookmark_id = int(query["id"][0]) if "id" in query else None
            url = query["url"][0] if "url" in query else None
            title = query["title"][0] if "title" in query else None
            description = query["description"][0] if "description" in query else None
            folder_id = int(query["folder_id"][0]) if "folder_id" in query else None
            is_favorite = (
                query["is_favorite"][0].lower() == "true"
                if "is_favorite" in query
                else None
            )
            BookmarkService().delete_by_criteria(
                bookmark_id=bookmark_id,
                url=url,
                title=title,
                description=description,
                folder_id=folder_id,
                is_favorite=is_favorite,
            )
            return self._ok(status_code=204)
        if method == "DELETE" and path == "/bookmarks/by-url" and "url" in query:
            BookmarkService().delete_by_url(query["url"][0])
            return self._ok(status_code=204)
        if (
            method == "DELETE"
            and path.startswith("/bookmarks/")
            and "/tags" not in path
        ):
            BookmarkService().delete_by_criteria(
                bookmark_id=int(path.rsplit("/", 1)[1])
            )
            return self._ok(status_code=204)
        if (
            method == "POST"
            and path.endswith("/tags")
            and path.startswith("/bookmarks/")
        ):
            bookmark_id = int(path.split("/")[2])
            body = TagAttach(**(json or {}))
            payload = BookmarkService().add_tag(bookmark_id, body.tag_id).model_dump()
            return self._ok(payload, 200)
        if method == "DELETE" and "/tags/" in path and path.startswith("/bookmarks/"):
            parts = path.split("/")
            BookmarkService().remove_tag(int(parts[2]), int(parts[4]))
            return self._ok(status_code=204)
        return None

    def _build_request(self, path: str) -> Request:
        parsed = urlparse(self.base_url)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        scope = {
            "type": "http",
            "scheme": parsed.scheme or "http",
            "server": (parsed.hostname or "testserver", port),
            "method": "GET",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "client": ("testclient", 50000),
        }
        return Request(scope)

    def request(self, method: str, url: str, json=None, **kwargs):
        params = kwargs.get("params")
        if params:
            query_string = urlencode(params, doseq=True)
            url = f"{url}?{query_string}"
        path, query = self._parse(url)

        try:
            if method == "GET" and path == "/health":
                return self._ok({"status": "ok"}, 200)
            if method == "GET" and path == "/metrics/dashboard":
                payload = DashboardService().metrics().model_dump()
                return self._ok(payload, 200)

            folders_response = self._handle_folders(method, path, json)
            if folders_response is not None:
                return folders_response

            tags_response = self._handle_tags(method, path, json)
            if tags_response is not None:
                return tags_response

            rss_feeds_response = self._handle_rss_feeds(method, path, query, json)
            if rss_feeds_response is not None:
                return rss_feeds_response

            news_sites_response = self._handle_news_sites(method, path, query, json)
            if news_sites_response is not None:
                return news_sites_response

            if method == "GET" and path == "/settings/llm":
                return self._ok(SettingsService().get_llm_settings().model_dump(), 200)
            if method == "PUT" and path == "/settings/llm":
                body = LLMSettingsUpdate(**(json or {}))
                return self._ok(
                    SettingsService().set_llm_settings(body).model_dump(), 200
                )
            if method == "DELETE" and path == "/settings/llm":
                SettingsService().delete_llm_settings()
                return self._ok(None, 204)
            if method == "POST" and path == "/settings/llm/test":
                body = LLMSettingsTestRequest(**(json or {}))
                return self._ok(
                    SettingsService().test_llm_settings(body).model_dump(), 200
                )

            if method == "GET" and path == "/settings/webhooks":
                payload = SettingsService().list_webhooks().model_dump()
                return self._ok(payload, 200)
            if method == "POST" and path == "/settings/webhooks":
                body = SettingsWebhookCreate(**(json or {}))
                payload = SettingsService().create_webhook(body).model_dump()
                return self._ok(payload, 201)
            if method == "PATCH" and path.startswith("/settings/webhooks/"):
                body = SettingsWebhookUpdate(**(json or {}))
                payload = SettingsService().update_webhook(
                    int(path.rsplit("/", 1)[1]), body
                ).model_dump()
                return self._ok(payload, 200)
            if method == "DELETE" and path.startswith("/settings/webhooks/"):
                SettingsService().delete_webhook(int(path.rsplit("/", 1)[1]))
                return self._ok(None, 204)
            if method == "POST" and path == "/settings/webhook/ping":
                body = SettingsWebhookPingRequest(**(json or {}))
                payload = SettingsService().ping_webhook(body).model_dump()
                return self._ok(payload, 200)
            if method == "GET" and path == "/settings/rss-execution":
                payload = SettingsService().get_rss_execution().model_dump()
                return self._ok(payload, 200)
            if method == "PUT" and path == "/settings/rss-execution":
                body = SettingsRssExecutionUpdate(**(json or {}))
                payload = SettingsService().set_rss_execution(body).model_dump()
                return self._ok(payload, 200)
            if method == "GET" and path == "/settings/rss-webhook-notification":
                payload = SettingsService().get_rss_webhook_notification().model_dump()
                return self._ok(payload, 200)
            if method == "PUT" and path == "/settings/rss-webhook-notification":
                body = SettingsRssWebhookNotificationUpdate(**(json or {}))
                payload = (
                    SettingsService().set_rss_webhook_notification(body).model_dump()
                )
                return self._ok(payload, 200)
            if method == "GET" and path == "/settings/webhook-summary":
                payload = SettingsService().get_webhook_summary().model_dump()
                return self._ok(payload, 200)
            if method == "PUT" and path == "/settings/webhook-summary":
                body = SettingsWebhookSummaryUpdate(**(json or {}))
                payload = SettingsService().set_webhook_summary(body).model_dump()
                return self._ok(payload, 200)
            bookmarks_response = self._handle_bookmarks(method, path, query, json)
            if bookmarks_response is not None:
                return bookmarks_response
        except ValidationError as exc:
            return self._error(422, exc.errors())
        except HTTPException as exc:
            return self._error(exc.status_code, exc.detail)
        except sqlite3.Error:
            return self._error(500, "Database error occurred")

        return self._error(404, "Not Found")

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request("POST", url, **kwargs)

    def patch(self, url: str, **kwargs):
        return self.request("PATCH", url, **kwargs)

    def put(self, url: str, **kwargs):
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs):
        return self.request("DELETE", url, **kwargs)
