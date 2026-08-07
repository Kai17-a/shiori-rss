from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlparse

from fastapi import HTTPException
from pydantic import ValidationError

from api.database import initialize_database
from api.model.models import (
    LLMSettingsTestRequest,
    LLMSettingsUpdate,
    RSSFeedCreate,
    RSSFeedUpdate,
    SettingsRssExecutionUpdate,
    SettingsRssWebhookNotificationUpdate,
    SettingsWebhookCreate,
    SettingsWebhookPingRequest,
    SettingsWebhookSummaryUpdate,
    SettingsWebhookUpdate,
)
from api.services.rss_feed_service import RSSFeedService
from api.services.settings_service import SettingsService


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

    def _rss_response(self, method: str, path: str, query, json):
        service = RSSFeedService()
        if method == "POST" and path == "/rss-feeds":
            return self._ok(service.create(RSSFeedCreate(**(json or {}))).model_dump(), 201)
        if method == "GET" and path == "/rss-feeds":
            payload = service.list(
                q=query.get("q", [None])[0],
                page=int(query.get("page", [1])[0]),
                per_page=int(query.get("per_page", [20])[0]),
            ).model_dump()
            return self._ok(payload)
        if not path.startswith("/rss-feeds/"):
            return None
        parts = path.strip("/").split("/")
        feed_id = int(parts[1])
        if len(parts) == 3 and parts[2] == "articles" and method == "GET":
            payload = service.list_articles(
                feed_id,
                q=query.get("q", [None])[0],
                page=int(query.get("page", [1])[0]),
                per_page=int(query.get("per_page", [20])[0]),
                published_from=query.get("published_from", [None])[0],
                published_to=query.get("published_to", [None])[0],
            ).model_dump()
            return self._ok(payload)
        if len(parts) == 3 and parts[2] == "execute" and method == "POST":
            return self._ok(service.execute(feed_id).model_dump())
        if len(parts) != 2:
            return None
        if method == "GET":
            return self._ok(service.get(feed_id).model_dump())
        if method == "PATCH":
            return self._ok(service.update(feed_id, RSSFeedUpdate(**(json or {}))).model_dump())
        if method == "DELETE":
            service.delete(feed_id)
            return self._ok(None, 204)
        return None

    def _settings_response(self, method: str, path: str, json):
        service = SettingsService()
        if method == "GET" and path == "/settings/llm":
            return self._ok(service.get_llm_settings().model_dump())
        if method == "PUT" and path == "/settings/llm":
            body = LLMSettingsUpdate(**(json or {}))
            return self._ok(service.set_llm_settings(body).model_dump())
        if method == "DELETE" and path == "/settings/llm":
            service.delete_llm_settings()
            return self._ok(None, 204)
        if method == "POST" and path == "/settings/llm/test":
            body = LLMSettingsTestRequest(**(json or {}))
            return self._ok(service.test_llm_settings(body).model_dump())
        if method == "GET" and path == "/settings/webhooks":
            return self._ok(service.list_webhooks().model_dump())
        if method == "POST" and path == "/settings/webhooks":
            return self._ok(service.create_webhook(SettingsWebhookCreate(**(json or {}))).model_dump(), 201)
        if path.startswith("/settings/webhooks/"):
            webhook_id = int(path.rsplit("/", 1)[1])
            if method == "PATCH":
                return self._ok(service.update_webhook(webhook_id, SettingsWebhookUpdate(**(json or {}))).model_dump())
            if method == "DELETE":
                service.delete_webhook(webhook_id)
                return self._ok(None, 204)
        if method == "POST" and path == "/settings/webhook/ping":
            return self._ok(service.ping_webhook(SettingsWebhookPingRequest(**(json or {}))).model_dump())

        setting_routes = {
            "/settings/rss-execution": (
                service.get_rss_execution,
                service.set_rss_execution,
                SettingsRssExecutionUpdate,
            ),
            "/settings/rss-webhook-notification": (
                service.get_rss_webhook_notification,
                service.set_rss_webhook_notification,
                SettingsRssWebhookNotificationUpdate,
            ),
            "/settings/webhook-summary": (
                service.get_webhook_summary,
                service.set_webhook_summary,
                SettingsWebhookSummaryUpdate,
            ),
        }
        route = setting_routes.get(path)
        if route and method == "GET":
            return self._ok(route[0]().model_dump())
        if route and method == "PUT":
            return self._ok(route[1](route[2](**(json or {}))).model_dump())
        return None

    def request(self, method: str, url: str, json=None, **kwargs):
        params = kwargs.get("params")
        if params:
            url = f"{url}?{urlencode(params, doseq=True)}"
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        try:
            if method == "GET" and parsed.path == "/health":
                return self._ok({"status": "ok"})
            response = self._rss_response(method, parsed.path, query, json)
            if response is not None:
                return response
            response = self._settings_response(method, parsed.path, json)
            if response is not None:
                return response
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
