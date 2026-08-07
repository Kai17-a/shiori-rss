from fastapi import APIRouter, Depends

from api.dependencies import get_settings_service
from api.model.models import (
    ErrorResponse,
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
from api.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/webhooks", status_code=200, response_model=SettingsWebhookListResponse)
def list_webhooks(service: SettingsService = Depends(get_settings_service)):
    return service.list_webhooks()


@router.post(
    "/webhooks",
    status_code=201,
    response_model=SettingsWebhookResponse,
    responses={
        409: {
            "model": ErrorResponse,
            "description": "Webhook URL is already registered",
        }
    },
)
def create_webhook(
    body: SettingsWebhookCreate,
    service: SettingsService = Depends(get_settings_service),
):
    return service.create_webhook(body)


@router.patch(
    "/webhooks/{webhook_id}", status_code=200, response_model=SettingsWebhookResponse
)
def update_webhook(
    webhook_id: int,
    body: SettingsWebhookUpdate,
    service: SettingsService = Depends(get_settings_service),
):
    return service.update_webhook(webhook_id, body)


@router.delete("/webhooks/{webhook_id}", status_code=204)
def delete_webhook(
    webhook_id: int,
    service: SettingsService = Depends(get_settings_service),
):
    service.delete_webhook(webhook_id)


@router.post(
    "/webhook/ping", status_code=200, response_model=SettingsWebhookPingResponse
)
def ping_webhook(
    body: SettingsWebhookPingRequest,
    service: SettingsService = Depends(get_settings_service),
):
    return service.ping_webhook(body)


@router.get(
    "/rss-execution", status_code=200, response_model=SettingsRssExecutionResponse
)
def get_rss_execution(service: SettingsService = Depends(get_settings_service)):
    return service.get_rss_execution()


@router.put(
    "/rss-execution", status_code=200, response_model=SettingsRssExecutionResponse
)
def set_rss_execution(
    body: SettingsRssExecutionUpdate,
    service: SettingsService = Depends(get_settings_service),
):
    return service.set_rss_execution(body)


@router.get(
    "/rss-webhook-notification",
    status_code=200,
    response_model=SettingsRssWebhookNotificationResponse,
)
def get_rss_webhook_notification(
    service: SettingsService = Depends(get_settings_service),
):
    return service.get_rss_webhook_notification()


@router.put(
    "/rss-webhook-notification",
    status_code=200,
    response_model=SettingsRssWebhookNotificationResponse,
)
def set_rss_webhook_notification(
    body: SettingsRssWebhookNotificationUpdate,
    service: SettingsService = Depends(get_settings_service),
):
    return service.set_rss_webhook_notification(body)


@router.get(
    "/webhook-summary", status_code=200, response_model=SettingsWebhookSummaryResponse
)
def get_webhook_summary(service: SettingsService = Depends(get_settings_service)):
    return service.get_webhook_summary()


@router.put(
    "/webhook-summary", status_code=200, response_model=SettingsWebhookSummaryResponse
)
def set_webhook_summary(
    body: SettingsWebhookSummaryUpdate,
    service: SettingsService = Depends(get_settings_service),
):
    return service.set_webhook_summary(body)
