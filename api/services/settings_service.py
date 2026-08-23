import sqlite3

import httpx
from fastapi import HTTPException

from api.database import get_db, recreate_vector_search_schema
from api.model.models import (
    LLMSettingsResponse,
    LLMSettingsTestRequest,
    LLMSettingsTestResponse,
    LLMSettingsUpdate,
    SettingsAIArticleAnalysisResponse,
    SettingsAIArticleAnalysisUpdate,
    SettingsRssExecutionResponse,
    SettingsRssExecutionUpdate,
    SettingsRssWebhookNotificationResponse,
    SettingsRssWebhookNotificationUpdate,
    SettingsWebhookArticleLimitResponse,
    SettingsWebhookArticleLimitUpdate,
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
from api.services.llm_service import (
    LLM_DEFAULT_TIMEOUT_SECONDS,
    LLM_EMBEDDING_DIM_SETTING_KEY,
    LLM_SETTING_KEYS,
    LLMConfig,
    load_llm_config,
    save_llm_config,
    test_embedding_connection,
    test_llm_connection,
)
from api.services.webhook_service import (
    build_webhook_payload,
    detect_webhook_service,
    send_webhook,
)

RSS_EXECUTION_SETTING_KEY = "rss_periodic_execution_enabled"
RSS_WEBHOOK_NOTIFICATION_SETTING_KEY = "rss_webhook_notification_enabled"
WEBHOOK_SUMMARY_SETTING_KEY = "webhook_include_summary_enabled"
WEBHOOK_ARTICLE_LIMIT_SETTING_KEY = "webhook_max_articles_per_run"
WEBHOOK_ARTICLE_LIMIT_DEFAULT = 20
AI_ARTICLE_ANALYSIS_ENABLED_KEY = "ai_article_analysis_enabled"
AI_ARTICLE_ANALYSIS_MAX_ARTICLES_KEY = "ai_article_analysis_max_articles_per_run"
AI_ARTICLE_ANALYSIS_DAILY_TOKEN_LIMIT_KEY = "ai_article_analysis_daily_token_limit"
AI_ARTICLE_ANALYSIS_LOOKBACK_DAYS_KEY = "ai_article_analysis_lookback_days"
AI_ARTICLE_ANALYSIS_DEFAULT_MAX_ARTICLES = 20
AI_ARTICLE_ANALYSIS_DEFAULT_DAILY_TOKEN_LIMIT = 50_000
AI_ARTICLE_ANALYSIS_DEFAULT_LOOKBACK_DAYS = 30


class SettingsService:
    @staticmethod
    def _get_int_setting(repo: SettingsRepository, key: str, default: int) -> int:
        return repo.get_int(key, default)

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

    def _to_llm_settings_response(self, config: LLMConfig) -> LLMSettingsResponse:
        return LLMSettingsResponse(
            provider=config.provider,
            base_url=config.base_url,
            api_key_configured=bool(config.api_key),
            model=config.model,
            embedding_model=config.embedding_model,
            timeout_seconds=config.timeout_seconds,
        )

    def get_llm_settings(self) -> LLMSettingsResponse:
        with get_db() as conn:
            config = load_llm_config(SettingsRepository(conn))
            if config is None:
                raise HTTPException(
                    status_code=404, detail="LLM settings are not configured"
                )
            return self._to_llm_settings_response(config)

    def set_llm_settings(self, data: LLMSettingsUpdate) -> LLMSettingsResponse:
        with get_db() as conn:
            saved = load_llm_config(SettingsRepository(conn))
        api_key = (
            None
            if data.clear_api_key
            else data.api_key or (saved.api_key if saved is not None else None)
        )
        config = LLMConfig(
            provider=data.provider,
            base_url=str(data.base_url),
            api_key=api_key,
            model=data.model,
            embedding_model=data.embedding_model,
            timeout_seconds=data.timeout_seconds,
        )
        test_llm_connection(config)
        if config.embedding_model:
            vector = test_embedding_connection(config)
            with get_db() as conn:
                repo = SettingsRepository(conn)
                previous_dim = repo.get_int(LLM_EMBEDDING_DIM_SETTING_KEY, 0)
                if previous_dim != len(vector):
                    # First time an embedding model is set, or switched to a
                    # differently-sized one: the vec0 table's width must
                    # match exactly, and any existing rows are for the old
                    # model's vector space anyway (already stale).
                    recreate_vector_search_schema(conn, len(vector))
                    repo.set(LLM_EMBEDDING_DIM_SETTING_KEY, str(len(vector)))
        with get_db() as conn:
            save_llm_config(SettingsRepository(conn), config)
        return self._to_llm_settings_response(config)

    def delete_llm_settings(self) -> None:
        with get_db() as conn:
            repo = SettingsRepository(conn)
            for key in LLM_SETTING_KEYS:
                repo.delete(key)
            repo.set(AI_ARTICLE_ANALYSIS_ENABLED_KEY, "0")

    def test_llm_settings(
        self, data: LLMSettingsTestRequest
    ) -> LLMSettingsTestResponse:
        with get_db() as conn:
            saved = load_llm_config(SettingsRepository(conn))
        config = self._merge_llm_config(saved, data)
        if config is None:
            raise HTTPException(
                status_code=400, detail="LLM settings are not configured"
            )
        reply = test_llm_connection(config)
        return LLMSettingsTestResponse(ok=True, reply=reply)

    def _merge_llm_config(
        self, saved: LLMConfig | None, data: LLMSettingsTestRequest
    ) -> LLMConfig | None:
        provider = data.provider or (saved.provider if saved else None)
        base_url = (
            str(data.base_url) if data.base_url else (saved.base_url if saved else None)
        )
        model = data.model.strip() if data.model else (saved.model if saved else None)
        if not provider or not base_url or not model:
            return None
        api_key = (
            None
            if data.clear_api_key
            else data.api_key
            if data.api_key is not None
            else (saved.api_key if saved else None)
        )
        embedding_model = (
            data.embedding_model
            if data.embedding_model is not None
            else (saved.embedding_model if saved else None)
        )
        timeout_seconds = (
            data.timeout_seconds
            if data.timeout_seconds is not None
            else (saved.timeout_seconds if saved else LLM_DEFAULT_TIMEOUT_SECONDS)
        )
        return LLMConfig(
            provider=provider,
            base_url=base_url,
            api_key=api_key,
            model=model,
            embedding_model=embedding_model,
            timeout_seconds=timeout_seconds,
        )

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

    def get_ai_article_analysis(self) -> SettingsAIArticleAnalysisResponse:
        with get_db() as conn:
            repo = SettingsRepository(conn)
            return SettingsAIArticleAnalysisResponse(
                enabled=repo.get(AI_ARTICLE_ANALYSIS_ENABLED_KEY) == "1",
                max_articles_per_run=self._get_int_setting(
                    repo,
                    AI_ARTICLE_ANALYSIS_MAX_ARTICLES_KEY,
                    AI_ARTICLE_ANALYSIS_DEFAULT_MAX_ARTICLES,
                ),
                daily_token_limit=self._get_int_setting(
                    repo,
                    AI_ARTICLE_ANALYSIS_DAILY_TOKEN_LIMIT_KEY,
                    AI_ARTICLE_ANALYSIS_DEFAULT_DAILY_TOKEN_LIMIT,
                ),
                lookback_days=self._get_int_setting(
                    repo,
                    AI_ARTICLE_ANALYSIS_LOOKBACK_DAYS_KEY,
                    AI_ARTICLE_ANALYSIS_DEFAULT_LOOKBACK_DAYS,
                ),
            )

    def set_ai_article_analysis(
        self, data: SettingsAIArticleAnalysisUpdate
    ) -> SettingsAIArticleAnalysisResponse:
        if data.enabled:
            with get_db() as conn:
                if load_llm_config(SettingsRepository(conn)) is None:
                    raise HTTPException(
                        status_code=409,
                        detail="Configure an LLM connection before enabling AI article analysis.",
                    )
        with get_db() as conn:
            repo = SettingsRepository(conn)
            repo.set(AI_ARTICLE_ANALYSIS_ENABLED_KEY, "1" if data.enabled else "0")
            repo.set(
                AI_ARTICLE_ANALYSIS_MAX_ARTICLES_KEY,
                str(data.max_articles_per_run),
            )
            repo.set(
                AI_ARTICLE_ANALYSIS_DAILY_TOKEN_LIMIT_KEY,
                str(data.daily_token_limit),
            )
            repo.set(AI_ARTICLE_ANALYSIS_LOOKBACK_DAYS_KEY, str(data.lookback_days))
        return self.get_ai_article_analysis()

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

    def get_webhook_article_limit(self) -> SettingsWebhookArticleLimitResponse:
        with get_db() as conn:
            max_articles = SettingsRepository(conn).get_int(
                WEBHOOK_ARTICLE_LIMIT_SETTING_KEY,
                WEBHOOK_ARTICLE_LIMIT_DEFAULT,
            )
        return SettingsWebhookArticleLimitResponse(max_articles=max_articles)

    def set_webhook_article_limit(
        self, data: SettingsWebhookArticleLimitUpdate
    ) -> SettingsWebhookArticleLimitResponse:
        with get_db() as conn:
            stored = SettingsRepository(conn).set(
                WEBHOOK_ARTICLE_LIMIT_SETTING_KEY,
                str(data.max_articles),
            )
        return SettingsWebhookArticleLimitResponse(max_articles=int(stored))
