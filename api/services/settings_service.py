import sqlite3

import httpx
from fastapi import HTTPException

from api.database import get_db
from api.model.models import (
    SettingsRssExecutionResponse,
    SettingsRssExecutionUpdate,
    SettingsRssWebhookNotificationResponse,
    SettingsRssWebhookNotificationUpdate,
    SettingsWebhookSummaryResponse,
    SettingsWebhookSummaryUpdate,
    SettingsWebhookCreate,
    SettingsWebhookListResponse,
    SettingsWebhookPingRequest,
    SettingsWebhookPingResponse,
    SettingsWebhookResponse,
    SettingsWebhookUpdate,
)
from api.repositories.settings_repo import SettingsRepository
from api.repositories.webhook_endpoint_repo import WebhookEndpointRepository
from api.services.webhook_service import (
    build_webhook_payload,
    detect_webhook_service,
    send_webhook,
)

RSS_EXECUTION_SETTING_KEY = "rss_periodic_execution_enabled"
RSS_WEBHOOK_NOTIFICATION_SETTING_KEY = "rss_webhook_notification_enabled"
WEBHOOK_SUMMARY_SETTING_KEY = "webhook_include_summary_enabled"


class SettingsService:
    def _validate_webhook_url(self, webhook_url: str) -> None:
        from urllib.parse import urlparse

        parsed = urlparse(webhook_url)
        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(
                status_code=422, detail="Webhook URL must be a valid URL"
            )

    def _to_webhook_response(self, row: dict) -> SettingsWebhookResponse:
        return SettingsWebhookResponse(
            id=int(row["id"]),
            name=str(row["name"]),
            webhook_url=str(row["url"]),
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_webhooks(self) -> SettingsWebhookListResponse:
        with get_db() as conn:
            repo = WebhookEndpointRepository(conn)
            return SettingsWebhookListResponse(
                items=[self._to_webhook_response(row) for row in repo.find_all()]
            )

    def create_webhook(self, data: SettingsWebhookCreate) -> SettingsWebhookResponse:
        with get_db() as conn:
            repo = WebhookEndpointRepository(conn)
            webhook_url = str(data.webhook_url)
            self._validate_webhook_url(webhook_url)
            detect_webhook_service(webhook_url)
            try:
                row = repo.insert(data.name, webhook_url)
            except sqlite3.IntegrityError as exc:
                raise HTTPException(
                    status_code=409, detail="Webhook URL is already registered"
                ) from exc
            return self._to_webhook_response(row)

    def update_webhook(
        self, webhook_id: int, data: SettingsWebhookUpdate
    ) -> SettingsWebhookResponse:
        with get_db() as conn:
            row = WebhookEndpointRepository(conn).update_enabled(
                webhook_id, data.enabled
            )
            if row is None:
                raise HTTPException(
                    status_code=404, detail="Webhook endpoint not found"
                )
            return self._to_webhook_response(row)

    def delete_webhook(self, webhook_id: int) -> None:
        with get_db() as conn:
            repo = WebhookEndpointRepository(conn)
            if not repo.delete(webhook_id):
                raise HTTPException(
                    status_code=404, detail="Webhook endpoint not found"
                )

    def ping_webhook(
        self, data: SettingsWebhookPingRequest
    ) -> SettingsWebhookPingResponse:
        webhook_url = str(data.webhook_url)
        self._validate_webhook_url(webhook_url)
        webhook_service = detect_webhook_service(webhook_url)

        try:
            response = send_webhook(
                webhook_url,
                build_webhook_payload(webhook_service, content="ping"),
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail="Failed to reach webhook",
            ) from exc

        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail="Failed to reach webhook",
            )

        return SettingsWebhookPingResponse(pong=True)

    def get_rss_execution(self) -> SettingsRssExecutionResponse:
        with get_db() as conn:
            repo = SettingsRepository(conn)
            return SettingsRssExecutionResponse(
                enabled=repo.get_bool(RSS_EXECUTION_SETTING_KEY)
            )

    def set_rss_execution(
        self, data: SettingsRssExecutionUpdate
    ) -> SettingsRssExecutionResponse:
        with get_db() as conn:
            repo = SettingsRepository(conn)
            return SettingsRssExecutionResponse(
                enabled=repo.set_bool(RSS_EXECUTION_SETTING_KEY, data.enabled)
            )

    def get_rss_webhook_notification(
        self,
    ) -> SettingsRssWebhookNotificationResponse:
        with get_db() as conn:
            repo = SettingsRepository(conn)
            return SettingsRssWebhookNotificationResponse(
                enabled=repo.get_bool(RSS_WEBHOOK_NOTIFICATION_SETTING_KEY)
            )

    def set_rss_webhook_notification(
        self, data: SettingsRssWebhookNotificationUpdate
    ) -> SettingsRssWebhookNotificationResponse:
        with get_db() as conn:
            repo = SettingsRepository(conn)
            return SettingsRssWebhookNotificationResponse(
                enabled=repo.set_bool(
                    RSS_WEBHOOK_NOTIFICATION_SETTING_KEY, data.enabled
                )
            )

    def get_webhook_summary(self) -> SettingsWebhookSummaryResponse:
        with get_db() as conn:
            repo = SettingsRepository(conn)
            return SettingsWebhookSummaryResponse(
                enabled=repo.get_bool(WEBHOOK_SUMMARY_SETTING_KEY, default=True)
            )

    def set_webhook_summary(
        self, data: SettingsWebhookSummaryUpdate
    ) -> SettingsWebhookSummaryResponse:
        with get_db() as conn:
            repo = SettingsRepository(conn)
            return SettingsWebhookSummaryResponse(
                enabled=repo.set_bool(WEBHOOK_SUMMARY_SETTING_KEY, data.enabled)
            )
