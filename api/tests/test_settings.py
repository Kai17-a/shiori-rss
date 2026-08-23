"""Unit tests for Settings API endpoints."""

import io
import json
import sqlite3
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.tests.test_support import build_test_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    build_test_db(db_path)

    import api.database as db_module
    import api.services.article_analysis_service as analysis_module
    import api.services.settings_service as settings_module

    @contextmanager
    def patched_get_db(database_url=db_path):
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    monkeypatch.setattr(db_module, "get_db", patched_get_db)
    monkeypatch.setattr(analysis_module, "get_db", patched_get_db)
    monkeypatch.setattr(settings_module, "get_db", patched_get_db)

    with TestClient(app) as c:
        yield c


def test_list_webhooks_returns_empty_list_when_unconfigured(client):
    resp = client.get("/settings/webhooks")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_create_and_list_webhooks_round_trip(client):
    first_url = "https://discord.com/api/webhooks/1/token"
    second_url = "https://hooks.slack.com/services/xxx/yyy/zzz"

    first = client.post(
        "/settings/webhooks",
        json={"name": "Discord alerts", "webhook_url": first_url},
    )
    assert first.status_code == 201
    assert first.json()["name"] == "Discord alerts"
    assert first.json()["webhook_url"] == first_url
    assert first.json()["enabled"] is True
    assert first.json()["id"]

    second = client.post(
        "/settings/webhooks",
        json={"name": "Slack alerts", "webhook_url": second_url},
    )
    assert second.status_code == 201
    assert second.json()["name"] == "Slack alerts"
    assert second.json()["webhook_url"] == second_url

    listed = client.get("/settings/webhooks")
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()["items"]] == [
        "Discord alerts",
        "Slack alerts",
    ]
    assert [item["webhook_url"] for item in listed.json()["items"]] == [
        first_url,
        second_url,
    ]
    assert [item["enabled"] for item in listed.json()["items"]] == [True, True]


def test_update_webhook_enabled_round_trip(client):
    created = client.post(
        "/settings/webhooks",
        json={
            "name": "Discord alerts",
            "webhook_url": "https://discord.com/api/webhooks/1/token",
        },
    ).json()

    disabled = client.patch(
        f"/settings/webhooks/{created['id']}", json={"enabled": False}
    )
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False

    listed = client.get("/settings/webhooks")
    assert listed.json()["items"][0]["enabled"] is False

    enabled = client.patch(
        f"/settings/webhooks/{created['id']}", json={"enabled": True}
    )
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is True


def test_update_missing_webhook_returns_404(client):
    resp = client.patch("/settings/webhooks/99999", json={"enabled": False})
    assert resp.status_code == 404


def test_create_webhook_rejects_blank_name(client):
    resp = client.post(
        "/settings/webhooks",
        json={"name": "   ", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    )
    assert resp.status_code == 422


def test_create_webhook_rejects_duplicate_url(client):
    webhook_url = "https://discord.com/api/webhooks/1/token"
    created = client.post(
        "/settings/webhooks", json={"name": "Test webhook", "webhook_url": webhook_url}
    )
    assert created.status_code == 201

    duplicate = client.post(
        "/settings/webhooks", json={"name": "Test webhook", "webhook_url": webhook_url}
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Webhook URL is already registered"


def test_delete_webhook_removes_it_from_the_list(client):
    created = client.post(
        "/settings/webhooks",
        json={
            "name": "Test webhook",
            "webhook_url": "https://discord.com/api/webhooks/1/token",
        },
    )
    webhook_id = created.json()["id"]

    deleted = client.delete(f"/settings/webhooks/{webhook_id}")
    assert deleted.status_code == 204

    listed = client.get("/settings/webhooks")
    assert listed.status_code == 200
    assert listed.json()["items"] == []


def test_delete_missing_webhook_returns_404(client):
    resp = client.delete("/settings/webhooks/99999")
    assert resp.status_code == 404


def test_create_webhook_rejects_discord_host_with_wrong_path(client):
    resp = client.post(
        "/settings/webhooks",
        json={
            "name": "Test webhook",
            "webhook_url": "https://discord.com/channels/1/2",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == (
        "Webhook URL must be a Discord, Slack, or Microsoft Teams webhook URL"
    )


def test_create_webhook_accepts_slack_url(client):
    webhook_url = "https://hooks.slack.com/services/xxx/yyy/zzz"
    resp = client.post(
        "/settings/webhooks", json={"name": "Test webhook", "webhook_url": webhook_url}
    )
    assert resp.status_code == 201
    assert resp.json()["webhook_url"] == webhook_url


@pytest.mark.parametrize(
    "webhook_url",
    [
        "https://example.webhook.office.com/webhookb2/id/token",
        "https://prod-01.japaneast.logic.azure.com/workflows/id/triggers/manual/paths/invoke?sig=token",
        "https://default.example.api.powerplatform.com/powerautomate/automations/direct/workflows/id/triggers/manual/paths/invoke?sig=token",
    ],
)
def test_create_webhook_accepts_microsoft_teams_urls(client, webhook_url):
    resp = client.post(
        "/settings/webhooks", json={"name": "Test webhook", "webhook_url": webhook_url}
    )
    assert resp.status_code == 201
    assert resp.json()["webhook_url"] == webhook_url


def test_ping_microsoft_teams_webhook_uses_adaptive_card(client, monkeypatch):
    import api.services.webhook_service as webhook_module

    captured = {}

    def fake_post(url, json, timeout=5.0):
        captured["json"] = json

        class Response:
            status_code = 202

        return Response()

    monkeypatch.setattr(webhook_module.httpx, "post", fake_post)
    resp = client.post(
        "/settings/webhook/ping",
        json={
            "webhook_url": "https://prod-01.japaneast.logic.azure.com/workflows/id/triggers/manual/paths/invoke?sig=token"
        },
    )
    assert resp.status_code == 200
    assert captured["json"]["type"] == "message"
    attachment = captured["json"]["attachments"][0]
    assert attachment["contentType"] == "application/vnd.microsoft.card.adaptive"
    assert attachment["content"]["body"][0]["text"] == "ping"


def test_ping_webhook_maps_httpx_error_to_502(client, monkeypatch):
    import httpx
    import api.services.webhook_service as webhook_module

    def fake_post(url, json, timeout=5.0):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(webhook_module.httpx, "post", fake_post)

    resp = client.post(
        "/settings/webhook/ping",
        json={
            "name": "Test webhook",
            "webhook_url": "https://discord.com/api/webhooks/1/token",
        },
    )
    assert resp.status_code == 502
    assert resp.json()["detail"] == "Failed to reach webhook"


def test_rss_execution_setting_can_toggle_true_and_false(client):
    first = client.get("/settings/rss-execution")
    assert first.status_code == 200
    assert first.json()["enabled"] is False

    enabled = client.put("/settings/rss-execution", json={"enabled": True})
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is True

    disabled = client.put("/settings/rss-execution", json={"enabled": False})
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False

    last = client.get("/settings/rss-execution")
    assert last.status_code == 200
    assert last.json()["enabled"] is False


def test_rss_webhook_notification_setting_can_toggle_true_and_false(client):
    first = client.get("/settings/rss-webhook-notification")
    assert first.status_code == 200
    assert first.json()["enabled"] is False

    enabled = client.put("/settings/rss-webhook-notification", json={"enabled": True})
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is True

    disabled = client.put("/settings/rss-webhook-notification", json={"enabled": False})
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False

    last = client.get("/settings/rss-webhook-notification")
    assert last.status_code == 200
    assert last.json()["enabled"] is False


def test_webhook_summary_setting_defaults_to_true_and_can_toggle(client):
    first = client.get("/settings/webhook-summary")
    assert first.status_code == 200
    assert first.json()["enabled"] is True

    disabled = client.put("/settings/webhook-summary", json={"enabled": False})
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False

    last = client.get("/settings/webhook-summary")
    assert last.status_code == 200
    assert last.json()["enabled"] is False


def test_webhook_article_limit_defaults_to_twenty_and_validates_range(client):
    first = client.get("/settings/webhook-article-limit")
    assert first.status_code == 200
    assert first.json()["max_articles"] == 20

    updated = client.put(
        "/settings/webhook-article-limit", json={"max_articles": 7}
    )
    assert updated.status_code == 200
    assert updated.json()["max_articles"] == 7

    invalid = client.put(
        "/settings/webhook-article-limit", json={"max_articles": 101}
    )
    assert invalid.status_code == 422


def test_ai_article_analysis_defaults_to_disabled(client):
    response = client.get("/settings/ai-article-analysis")

    assert response.status_code == 200
    assert response.json() == {
        "enabled": False,
        "max_articles_per_run": 20,
        "daily_token_limit": 50000,
        "lookback_days": 30,
    }


def test_ai_article_analysis_requires_llm_before_enabling(client):
    response = client.put(
        "/settings/ai-article-analysis",
        json={
            "enabled": True,
            "max_articles_per_run": 10,
            "daily_token_limit": 20000,
            "lookback_days": 14,
        },
    )

    assert response.status_code == 409
    assert "Configure an LLM connection" in response.json()["detail"]


def test_ai_article_analysis_settings_round_trip(client):
    import api.services.settings_service as settings_module

    with settings_module.get_db() as conn:
        repo = settings_module.SettingsRepository(conn)
        repo.set("llm_provider", "openai")
        repo.set("llm_base_url", "https://llm.example.com/v1")
        repo.set("llm_model", "example-model")

    response = client.put(
        "/settings/ai-article-analysis",
        json={
            "enabled": True,
            "max_articles_per_run": 10,
            "daily_token_limit": 20000,
            "lookback_days": 14,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "enabled": True,
        "max_articles_per_run": 10,
        "daily_token_limit": 20000,
        "lookback_days": 14,
    }


def test_ai_article_analysis_can_run_manually_while_schedule_is_disabled(
    client, monkeypatch
):
    import api.services.article_analysis_service as analysis_module

    monkeypatch.setenv("SHIORI_FEED_BATCH_BIN", "/tmp/mock-shiori-feed-batch")

    class BatchProcess:
        pid = 4242

        def __init__(self):
            self.stdout = io.StringIO(
                "Analyzing article rss:1 (1/20)\n"
                '{"processed":2,"succeeded":2,"failed":0,'
                '"skipped_current":3,"stopped_by_token_limit":false}\n'
            )

        def wait(self):
            return 0

        def kill(self):
            return None

    def open_batch(command, **kwargs):
        assert command == ["/tmp/mock-shiori-feed-batch", "--article-analysis-only"]
        assert kwargs["stderr"] is analysis_module.subprocess.STDOUT
        return BatchProcess()

    monkeypatch.setattr(
        analysis_module.subprocess,
        "Popen",
        open_batch,
    )

    response = client.post("/settings/ai-article-analysis/execute")

    assert response.status_code == 200
    assert response.json() == {
        "processed": 2,
        "succeeded": 2,
        "failed": 0,
        "skipped_current": 3,
        "stopped_by_token_limit": False,
        "stopped_by_user": False,
    }


def test_ai_article_analysis_can_reanalyze_a_single_article(client, monkeypatch):
    import api.services.article_analysis_service as analysis_module

    monkeypatch.setenv("SHIORI_FEED_BATCH_BIN", "/tmp/mock-shiori-feed-batch")

    class BatchProcess:
        pid = 4242

        def __init__(self):
            self.stdout = io.StringIO(
                '{"processed":1,"succeeded":1,"failed":0,'
                '"skipped_current":0,"stopped_by_token_limit":false}\n'
            )

        def wait(self):
            return 0

        def kill(self):
            return None

    def open_batch(command, **kwargs):
        assert command == [
            "/tmp/mock-shiori-feed-batch",
            "--reanalyze-article=rss:7",
        ]
        assert kwargs["stderr"] is analysis_module.subprocess.STDOUT
        return BatchProcess()

    monkeypatch.setattr(analysis_module.subprocess, "Popen", open_batch)

    response = client.post("/settings/ai-article-analysis/rss/7/execute")

    assert response.status_code == 200
    assert response.json() == {
        "processed": 1,
        "succeeded": 1,
        "failed": 0,
        "skipped_current": 0,
        "stopped_by_token_limit": False,
        "stopped_by_user": False,
    }


def test_ai_article_analysis_reanalyze_rejects_an_unknown_source_type(client):
    response = client.post("/settings/ai-article-analysis/unknown/7/execute")

    assert response.status_code == 422


def test_ai_article_analysis_reanalyze_is_blocked_while_a_batch_run_is_active(
    client, monkeypatch
):
    import api.services.article_analysis_service as analysis_module

    assert analysis_module._manual_run_lock.acquire(blocking=False)
    try:
        response = client.post("/settings/ai-article-analysis/rss/7/execute")
        assert response.status_code == 409
    finally:
        analysis_module._manual_run_lock.release()


def test_ai_article_analysis_status_reports_manual_run(client):
    import api.services.article_analysis_service as analysis_module

    assert client.get("/settings/ai-article-analysis/status").json()["running"] is False
    assert analysis_module._manual_run_lock.acquire(blocking=False)
    try:
        response = client.get("/settings/ai-article-analysis/status")
        assert response.status_code == 200
        assert response.json()["running"] is True
    finally:
        analysis_module._manual_run_lock.release()


def test_ai_article_analysis_status_reports_batch_lock(client):
    import api.services.article_analysis_service as analysis_module

    with analysis_module.get_db() as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?)",
            (
                "ai_article_analysis_running",
                f"{int(analysis_module.time.time())}:{analysis_module.os.getpid()}",
            ),
        )

    response = client.get("/settings/ai-article-analysis/status")

    assert response.status_code == 200
    assert response.json()["running"] is True


def test_ai_article_analysis_status_returns_batch_progress(client):
    import api.services.article_analysis_service as analysis_module

    with analysis_module.get_db() as conn:
        conn.executemany(
            "INSERT INTO app_settings (key, value) VALUES (?, ?)",
            [
                (
                    "ai_article_analysis_running",
                    f"{int(analysis_module.time.time())}:{analysis_module.os.getpid()}",
                ),
                (
                    "ai_article_analysis_progress",
                    json.dumps(
                        {
                            "total": 10,
                            "processed": 4,
                            "succeeded": 3,
                            "failed": 1,
                            "skipped_current": 2,
                            "current_article_title": "Vue 3.5 released",
                            "tokens_used_today": 1250,
                            "daily_token_limit": 50000,
                            "started_at": 1786492800,
                        }
                    ),
                ),
            ],
        )

    response = client.get("/settings/ai-article-analysis/status")

    assert response.status_code == 200
    assert response.json() == {
        "running": True,
        "stopping": False,
        "total": 10,
        "processed": 4,
        "succeeded": 3,
        "failed": 1,
        "skipped_current": 2,
        "current_article_title": "Vue 3.5 released",
        "tokens_used_today": 1250,
        "daily_token_limit": 50000,
        "started_at": 1786492800,
    }


def test_ai_article_analysis_cancel_requests_stop_for_current_lock(client):
    import api.services.article_analysis_service as analysis_module

    token = f"{int(analysis_module.time.time())}:{analysis_module.os.getpid()}"
    with analysis_module.get_db() as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?)",
            ("ai_article_analysis_running", token),
        )

    response = client.post("/settings/ai-article-analysis/cancel")

    assert response.status_code == 202
    assert response.json() == {"cancellation_requested": True}
    status = client.get("/settings/ai-article-analysis/status").json()
    assert status["running"] is True
    assert status["stopping"] is True
    with analysis_module.get_db() as conn:
        value = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            ("ai_article_analysis_cancel_requested",),
        ).fetchone()[0]
    assert value == token


def test_ai_article_analysis_cancel_is_rejected_when_idle(client):
    response = client.post("/settings/ai-article-analysis/cancel")

    assert response.status_code == 409
    assert response.json()["detail"] == "Article analysis is not running"


def test_ai_article_analysis_status_clears_legacy_orphan_lock(client, monkeypatch):
    import api.services.article_analysis_service as analysis_module

    monkeypatch.setattr(analysis_module, "_legacy_batch_is_alive", lambda: False)
    with analysis_module.get_db() as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?)",
            ("ai_article_analysis_running", str(int(analysis_module.time.time()))),
        )

    response = client.get("/settings/ai-article-analysis/status")

    assert response.status_code == 200
    assert response.json()["running"] is False


def test_ai_article_analysis_clears_its_batch_lock_after_failure(client, monkeypatch):
    import api.services.article_analysis_service as analysis_module

    monkeypatch.setenv("SHIORI_FEED_BATCH_BIN", "/tmp/mock-shiori-feed-batch")

    class FailedBatchProcess:
        pid = 4243
        stdout = io.StringIO("LLM request failed\n")

        def wait(self):
            return 1

        def kill(self):
            return None

    def open_batch(*_args, **_kwargs):
        with analysis_module.get_db() as conn:
            conn.execute(
                "INSERT INTO app_settings (key, value) VALUES (?, ?)",
                (
                    "ai_article_analysis_running",
                    f"{int(analysis_module.time.time())}:{FailedBatchProcess.pid}",
                ),
            )
        return FailedBatchProcess()

    monkeypatch.setattr(analysis_module.subprocess, "Popen", open_batch)

    response = client.post("/settings/ai-article-analysis/execute")

    assert response.status_code == 502
    assert client.get("/settings/ai-article-analysis/status").json()["running"] is False


def test_llm_settings_are_tested_before_save_and_do_not_expose_api_key(
    client, monkeypatch
):
    import api.services.settings_service as settings_module

    tested = []
    monkeypatch.setattr(
        settings_module,
        "test_llm_connection",
        lambda config: tested.append(config) or "pong",
    )
    saved = client.put(
        "/settings/llm",
        json={
            "provider": "openai",
            "base_url": "https://llm.example.com/v1",
            "api_key": "secret-token",
            "model": "example-model",
        },
    )

    assert saved.status_code == 200
    assert saved.json() == {
        "provider": "openai",
        "base_url": "https://llm.example.com/v1",
        "api_key_configured": True,
        "model": "example-model",
        "embedding_model": None,
        "timeout_seconds": 90,
    }
    assert tested[0].api_key == "secret-token"
    assert tested[0].timeout_seconds == 90
    assert client.get("/settings/llm").json() == saved.json()


def test_llm_settings_accepts_and_tests_an_optional_embedding_model(client, monkeypatch):
    import api.services.settings_service as settings_module

    monkeypatch.setattr(settings_module, "test_llm_connection", lambda _config: "pong")
    monkeypatch.setattr(
        settings_module, "test_embedding_connection", lambda _config: [0.1, 0.2, 0.3]
    )

    saved = client.put(
        "/settings/llm",
        json={
            "provider": "openai",
            "base_url": "https://llm.example.com/v1",
            "model": "example-model",
            "embedding_model": "example-embedding-model",
        },
    )

    assert saved.status_code == 200
    assert saved.json()["embedding_model"] == "example-embedding-model"
    assert client.get("/settings/llm").json()["embedding_model"] == "example-embedding-model"


def test_llm_settings_timeout_defaults_to_90_seconds_and_can_be_overridden(
    client, monkeypatch
):
    import api.services.settings_service as settings_module

    tested = []
    monkeypatch.setattr(
        settings_module,
        "test_llm_connection",
        lambda config: tested.append(config) or "pong",
    )

    default = client.put(
        "/settings/llm",
        json={
            "provider": "openai",
            "base_url": "https://llm.example.com/v1",
            "model": "example-model",
        },
    )
    assert default.json()["timeout_seconds"] == 90
    assert tested[-1].timeout_seconds == 90

    custom = client.put(
        "/settings/llm",
        json={
            "provider": "openai",
            "base_url": "https://llm.example.com/v1",
            "model": "example-model",
            "timeout_seconds": 30,
        },
    )
    assert custom.status_code == 200
    assert custom.json()["timeout_seconds"] == 30
    assert tested[-1].timeout_seconds == 30
    assert client.get("/settings/llm").json()["timeout_seconds"] == 30


def test_llm_settings_rejects_a_timeout_outside_the_allowed_range(client):
    response = client.put(
        "/settings/llm",
        json={
            "provider": "openai",
            "base_url": "https://llm.example.com/v1",
            "model": "example-model",
            "timeout_seconds": 1,
        },
    )

    assert response.status_code == 422


def test_llm_request_uses_the_configured_timeout(client, monkeypatch):
    """The saved timeout_seconds must actually reach the outgoing HTTP call,
    not just round-trip through the settings API.
    """
    import api.services.settings_service as settings_module
    import api.services.llm_service as llm_module

    monkeypatch.setattr(settings_module, "test_llm_connection", lambda _config: "pong")
    client.put(
        "/settings/llm",
        json={
            "provider": "openai",
            "base_url": "https://llm.example.com/v1",
            "model": "example-model",
            "timeout_seconds": 15,
        },
    )

    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["timeout"] = timeout
        return type(
            "Resp",
            (),
            {
                "status_code": 200,
                "json": lambda self: {
                    "choices": [{"message": {"content": "pong"}}]
                },
            },
        )()

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)

    from api.database import get_db
    from api.repositories.settings_repo import SettingsRepository
    from api.services.llm_service import load_llm_config, chat_completion

    with get_db() as conn:
        config = load_llm_config(SettingsRepository(conn))
    assert config is not None

    chat_completion(config, [{"role": "user", "content": "hi"}], max_tokens=8)

    assert captured["timeout"] == 15


def test_llm_settings_recreates_vector_schema_when_model_dimension_changes(
    client, monkeypatch
):
    """No fixed dimension cap: the article_ai_embeddings table is recreated
    at whatever width the currently configured embedding model actually
    produces, however large (e.g. a 4096-dim cloud model)."""
    import api.services.article_analysis_service as analysis_module
    import api.services.settings_service as settings_module
    from api.database import load_vec_extension, pack_embedding

    monkeypatch.setattr(settings_module, "test_llm_connection", lambda _config: "pong")

    monkeypatch.setattr(
        settings_module, "test_embedding_connection", lambda _config: [0.1] * 4096
    )
    saved = client.put(
        "/settings/llm",
        json={
            "provider": "openai",
            "base_url": "https://llm.example.com/v1",
            "model": "example-model",
            "embedding_model": "large-embedding-model",
        },
    )
    assert saved.status_code == 200

    with analysis_module.get_db() as conn:
        load_vec_extension(conn)
        # The table must now accept a 4096-dim vector...
        conn.execute(
            "INSERT INTO article_ai_embeddings(analysis_id, embedding) VALUES (1, ?)",
            (pack_embedding([0.1] * 4096),),
        )
        # ...and reject a mismatched size, confirming the width really changed
        # rather than merely accepting anything.
        with pytest.raises(sqlite3.OperationalError):
            conn.execute(
                "INSERT INTO article_ai_embeddings(analysis_id, embedding) VALUES (2, ?)",
                (pack_embedding([0.1] * 8),),
            )

    # Switching to a differently-sized model recreates the table again.
    monkeypatch.setattr(
        settings_module, "test_embedding_connection", lambda _config: [0.1] * 8
    )
    switched = client.put(
        "/settings/llm",
        json={
            "provider": "openai",
            "base_url": "https://llm.example.com/v1",
            "model": "example-model",
            "embedding_model": "small-embedding-model",
        },
    )
    assert switched.status_code == 200

    with analysis_module.get_db() as conn:
        load_vec_extension(conn)
        # The old 4096-dim row is gone (table was dropped and recreated)...
        assert conn.execute("SELECT COUNT(*) FROM article_ai_embeddings").fetchone()[0] == 0
        # ...and it now accepts the new model's 8-dim vectors.
        conn.execute(
            "INSERT INTO article_ai_embeddings(analysis_id, embedding) VALUES (1, ?)",
            (pack_embedding([0.1] * 8),),
        )


def test_clearing_embedding_model_does_not_delete_existing_embeddings(
    client, monkeypatch
):
    import api.services.article_analysis_service as analysis_module
    import api.services.settings_service as settings_module
    from api.database import load_vec_extension, pack_embedding

    monkeypatch.setattr(settings_module, "test_llm_connection", lambda _config: "pong")
    monkeypatch.setattr(
        settings_module, "test_embedding_connection", lambda _config: [0.1, 0.2]
    )
    client.put(
        "/settings/llm",
        json={
            "provider": "openai",
            "base_url": "https://llm.example.com/v1",
            "model": "example-model",
            "embedding_model": "example-embedding-model",
        },
    )
    with analysis_module.get_db() as conn:
        analysis_id = conn.execute(
            """
            INSERT INTO article_ai_analyses (
                source_type, article_id, content_hash, model, prompt_version, status,
                embedding_model, embedding_dim
            ) VALUES ('rss', 1, 'hash', 'example-model', 'article-analysis-v3',
                      'completed', 'example-embedding-model', 2)
            """
        ).lastrowid
        load_vec_extension(conn)
        conn.execute(
            "INSERT INTO article_ai_embeddings(analysis_id, embedding) VALUES (?, ?)",
            (analysis_id, pack_embedding([0.1, 0.2])),
        )

    # Clear the embedding model (send it back as null) without touching the
    # chat model — this must not delete the embedding rows already saved.
    cleared = client.put(
        "/settings/llm",
        json={
            "provider": "openai",
            "base_url": "https://llm.example.com/v1",
            "model": "example-model",
            "embedding_model": None,
        },
    )

    assert cleared.status_code == 200
    assert cleared.json()["embedding_model"] is None
    with analysis_module.get_db() as conn:
        assert (
            conn.execute("SELECT COUNT(*) FROM article_ai_analyses WHERE embedding_model IS NOT NULL")
            .fetchone()[0]
            == 1
        )
        load_vec_extension(conn)
        assert conn.execute("SELECT COUNT(*) FROM article_ai_embeddings").fetchone()[0] == 1


def test_clear_ai_analysis_results_keeps_daily_token_usage(client):
    import api.services.article_analysis_service as analysis_module

    with analysis_module.get_db() as conn:
        conn.execute(
            """
            INSERT INTO article_ai_analyses (
                source_type, article_id, content_hash, model, prompt_version,
                ai_summary, status
            ) VALUES ('rss', 1, 'hash', 'model', 'article-analysis-v2',
                      'Saved summary', 'completed')
            """
        )
        conn.execute(
            """
            INSERT INTO article_ai_analysis_usage (
                source_type, article_id, input_tokens, output_tokens, successful
            ) VALUES ('rss', 1, 100, 20, 1)
            """
        )

    response = client.delete("/settings/ai-article-analysis/results")

    assert response.status_code == 200
    assert response.json() == {"cleared_count": 1}
    with analysis_module.get_db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM article_ai_analyses").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM article_ai_search").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM article_ai_analysis_usage").fetchone()[0] == 1


def test_clear_ai_analysis_results_also_removes_orphaned_embeddings(client):
    import api.services.article_analysis_service as analysis_module
    from api.database import load_vec_extension, pack_embedding

    with analysis_module.get_db() as conn:
        analysis_id = conn.execute(
            """
            INSERT INTO article_ai_analyses (
                source_type, article_id, content_hash, model, prompt_version, status
            ) VALUES ('rss', 1, 'hash', 'model', 'article-analysis-v3', 'completed')
            """
        ).lastrowid
        load_vec_extension(conn)
        conn.execute(
            "INSERT INTO article_ai_embeddings(analysis_id, embedding) VALUES (?, ?)",
            (analysis_id, pack_embedding([0.1] * 8)),
        )

    response = client.delete("/settings/ai-article-analysis/results")

    assert response.status_code == 200
    with analysis_module.get_db() as conn:
        load_vec_extension(conn)
        assert conn.execute("SELECT COUNT(*) FROM article_ai_embeddings").fetchone()[0] == 0


def test_clear_ai_analysis_results_is_blocked_while_running(client, monkeypatch):
    import api.services.article_analysis_service as analysis_module

    monkeypatch.setattr(
        analysis_module.ArticleAnalysisService,
        "status",
        lambda _self: analysis_module.SettingsAIArticleAnalysisStatusResponse(running=True),
    )

    response = client.delete("/settings/ai-article-analysis/results")

    assert response.status_code == 409
    assert "running" in response.json()["detail"]


def test_delete_failed_ai_analysis_results_is_blocked_while_running(
    client, monkeypatch
):
    import api.services.article_analysis_service as analysis_module

    monkeypatch.setattr(
        analysis_module.ArticleAnalysisService,
        "status",
        lambda _self: analysis_module.SettingsAIArticleAnalysisStatusResponse(
            running=True
        ),
    )

    response = client.delete("/ai/article-analyses/failed")

    assert response.status_code == 409
    assert "running" in response.json()["detail"]


def test_llm_settings_are_not_saved_when_connection_test_fails(client, monkeypatch):
    from fastapi import HTTPException
    import api.services.settings_service as settings_module

    def fail(_config):
        raise HTTPException(status_code=502, detail="Failed to reach LLM server")

    monkeypatch.setattr(settings_module, "test_llm_connection", fail)
    failed = client.put(
        "/settings/llm",
        json={
            "provider": "ollama",
            "base_url": "http://127.0.0.1:11434",
            "model": "llama3.2",
        },
    )

    assert failed.status_code == 502
    assert client.get("/settings/llm").status_code == 404


def test_llm_test_can_use_saved_settings_and_settings_can_be_deleted(
    client, monkeypatch
):
    import api.services.settings_service as settings_module

    monkeypatch.setattr(settings_module, "test_llm_connection", lambda _config: "pong")
    client.put(
        "/settings/llm",
        json={
            "provider": "vllm",
            "base_url": "http://127.0.0.1:8000/v1",
            "model": "local-model",
        },
    )

    tested = client.post("/settings/llm/test", json={})
    assert tested.status_code == 200
    assert tested.json() == {"ok": True, "reply": "pong"}

    analysis = client.put(
        "/settings/ai-article-analysis",
        json={
            "enabled": True,
            "max_articles_per_run": 20,
            "daily_token_limit": 50000,
            "lookback_days": 30,
        },
    )
    assert analysis.status_code == 200

    assert client.delete("/settings/llm").status_code == 204
    assert client.get("/settings/llm").status_code == 404
    assert client.get("/settings/ai-article-analysis").json()["enabled"] is False
