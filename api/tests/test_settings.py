"""Unit tests for Settings API endpoints."""

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
    }
    assert tested[0].api_key == "secret-token"
    assert client.get("/settings/llm").json() == saved.json()


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

    assert client.delete("/settings/llm").status_code == 204
    assert client.get("/settings/llm").status_code == 404
