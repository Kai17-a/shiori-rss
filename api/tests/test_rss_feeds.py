"""Unit tests for RSS feed API endpoints."""

import sqlite3
from contextlib import contextmanager
from typing import cast

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.tests.test_support import build_test_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    build_test_db(db_path)

    import api.database as db_module
    import api.services.rss_feed_service as rss_module
    import api.services.settings_service as settings_module
    import api.services.webhook_service as webhook_module

    def fake_get(url, timeout=5.0, follow_redirects=True):
        class Response:
            status_code = 200
            text = "<?xml version='1.0'?><rss><channel><title>Example</title></channel></rss>"
            content = b"<?xml version='1.0'?><rss><channel><title>Example</title></channel></rss>"

        return Response()

    def fake_post(url, json, timeout=5.0):
        class Response:
            status_code = 204

        return Response()

    def fake_parse(content):
        class ParsedEntry:
            def __init__(self, title, link):
                self._title = title
                self._link = link

            def get(self, key, default=None):
                data = {
                    "title": self._title,
                    "link": self._link,
                }
                return data.get(key, default)

        class ParsedFeed:
            bozo = False
            feed = {"title": "Parsed Example"}
            entries = [
                ParsedEntry("Item 1", "https://example.com/item-1"),
                ParsedEntry("Item 2", "https://example.com/item-2"),
            ]

        return ParsedFeed()

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
    monkeypatch.setattr(rss_module, "get_db", patched_get_db)
    monkeypatch.setattr(settings_module, "get_db", patched_get_db)
    monkeypatch.setattr(rss_module.httpx, "get", fake_get)
    monkeypatch.setattr(rss_module.feedparser, "parse", fake_parse)
    monkeypatch.setattr(webhook_module.httpx, "post", fake_post)

    with TestClient(app) as c:
        yield c


def create_feed(client, url="https://example.com/feed.xml", title="Example"):
    return client.post("/rss-feeds", json={"url": url, "title": title})


def test_create_rss_feed_returns_201(client):
    resp = create_feed(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["url"] == "https://example.com/feed.xml"
    assert body["title"] == "Example"
    assert body["notify_webhook_enabled"] is True
    assert "id" in body


def test_rss_feed_icon_can_be_uploaded_and_served(client):
    feed_id = create_feed(client).json()["id"]
    response = client.put(
        f"/rss-feeds/{feed_id}/icon",
        data={"public_url": f"https://feeds.example.com/api/rss-feeds/{feed_id}/icon"},
        files={"file": ("icon.png", b"png-bytes", "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["icon_uploaded"] is True
    assert response.json()["icon_url"].endswith(f"/rss-feeds/{feed_id}/icon")

    icon = client.get(f"/rss-feeds/{feed_id}/icon")
    assert icon.status_code == 200
    assert icon.content == b"png-bytes"
    assert icon.headers["content-type"] == "image/png"


def test_rss_feed_accepts_external_icon_url(client):
    response = client.post(
        "/rss-feeds",
        json={
            "url": "https://example.com/feed.xml",
            "title": "Example",
            "icon_url": "https://cdn.example.com/feed.png",
        },
    )

    assert response.status_code == 201
    assert response.json()["icon_url"] == "https://cdn.example.com/feed.png"
    assert response.json()["icon_uploaded"] is False


def test_discord_rss_payload_uses_feed_icon():
    from api.services.webhook_service import build_rss_notification_payload

    payload = build_rss_notification_payload(
        "discord",
        feed_title="Example",
        articles=[],
        icon_url="https://cdn.example.com/feed.png",
    )

    assert payload["avatar_url"] == "https://cdn.example.com/feed.png"


def test_register_webhook_accepts_slack_webhook_url(client):
    resp = client.post(
        "/settings/webhooks",
        json={
            "name": "Slack alerts",
            "webhook_url": "https://hooks.slack.com/services/xxx/yyy/zzz",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Slack alerts"
    assert resp.json()["webhook_url"] == "https://hooks.slack.com/services/xxx/yyy/zzz"


def test_execute_rss_feed_supports_microsoft_teams_adaptive_cards(client, monkeypatch):
    import api.services.webhook_service as webhook_module

    payloads = []

    def fake_post(url, json, timeout=5.0):
        payloads.append(json)

        class Response:
            status_code = 202

        return Response()

    monkeypatch.setattr(webhook_module.httpx, "post", fake_post)
    client.post(
        "/settings/webhooks",
        json={
            "name": "Teams alerts",
            "webhook_url": "https://prod-01.japaneast.logic.azure.com/workflows/id/triggers/manual/paths/invoke?sig=token"
        },
    )
    feed_id = create_feed(client).json()["id"]

    resp = client.post(f"/rss-feeds/{feed_id}/execute")

    assert resp.status_code == 200
    card = payloads[0]["attachments"][0]["content"]
    assert card["type"] == "AdaptiveCard"
    assert card["body"][0]["text"] == "Parsed Example - New articles (2 items)"
    first_article = card["body"][1]["items"]
    assert card["body"][1]["spacing"] == "Medium"
    assert "separator" not in card["body"][1]
    assert first_article[0]["text"] == "- [Item 1](https://example.com/item-1)"
    assert not any(item["type"] == "ActionSet" for item in first_article)

    summary_payload = webhook_module.build_rss_notification_payload(
        "teams",
        feed_title="Example",
        articles=[
            {
                "title": "Article",
                "url": "https://example.com/article",
                "summary": "Summary",
            }
        ],
    )
    attachments = cast(list[dict[str, object]], summary_payload["attachments"])
    content = cast(dict[str, object], attachments[0]["content"])
    body = cast(list[dict[str, object]], content["body"])
    summary_items = cast(list[dict[str, object]], body[1]["items"])
    assert summary_items[1]["spacing"] == "Small"


def test_execute_rss_feed_truncates_long_article_content_for_discord(client, monkeypatch):
    import api.services.rss_feed_service as rss_module
    import api.services.webhook_service as webhook_module

    payloads = []

    def fake_post(url, json, timeout=5.0):
        payloads.append(json)

        class Response:
            status_code = 204

        return Response()

    monkeypatch.setattr(webhook_module.httpx, "post", fake_post)
    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    )
    feed_id = create_feed(client).json()["id"]

    class ParsedEntry:
        def get(self, key, default=None):
            data = {
                "title": "T" * 400,
                "link": "https://example.com/item-1",
                "summary": "S" * 20000,
            }
            return data.get(key, default)

    class ParsedFeed:
        bozo = False
        feed = {"title": "Parsed Example"}
        entries = [ParsedEntry()]

    monkeypatch.setattr(rss_module.feedparser, "parse", lambda content: ParsedFeed())

    resp = client.post(f"/rss-feeds/{feed_id}/execute")

    assert resp.status_code == 200
    embed = payloads[0]["embeds"][0]
    assert len(embed["title"]) <= 256
    assert len(embed["description"]) <= 300
    assert embed["title"].endswith("…")
    assert embed["description"].endswith("…")


def test_execute_rss_feed_can_omit_article_summaries(client, monkeypatch):
    import api.services.rss_feed_service as rss_module
    import api.services.webhook_service as webhook_module

    payloads = []

    def fake_post(url, json, timeout=5.0):
        payloads.append(json)

        class Response:
            status_code = 204

        return Response()

    monkeypatch.setattr(webhook_module.httpx, "post", fake_post)
    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    )
    client.put("/settings/webhook-summary", json={"enabled": False})
    feed_id = create_feed(client).json()["id"]

    class ParsedEntry:
        def get(self, key, default=None):
            return {
                "title": "Example article",
                "link": "https://example.com/no-summary-notification",
                "summary": "This summary must not be sent.",
            }.get(key, default)

    class ParsedFeed:
        bozo = False
        feed = {"title": "Parsed Example"}
        entries = [ParsedEntry()]

    monkeypatch.setattr(rss_module.feedparser, "parse", lambda content: ParsedFeed())

    response = client.post(f"/rss-feeds/{feed_id}/execute")

    assert response.status_code == 200
    assert "description" not in payloads[0]["embeds"][0]


def test_ping_webhook_returns_200(client, monkeypatch):
    import api.services.webhook_service as webhook_module

    captured = {}

    def fake_post(url, json, timeout=5.0):
        captured["url"] = url
        captured["json"] = json

        class Response:
            status_code = 204

        return Response()

    monkeypatch.setattr(webhook_module.httpx, "post", fake_post)
    resp = client.post(
        "/settings/webhook/ping",
        json={"name": "Test webhook", "webhook_url": "https://hooks.slack.com/services/xxx/yyy/zzz"},
    )
    assert resp.status_code == 200
    assert resp.json()["pong"] is True
    assert captured == {
        "url": "https://hooks.slack.com/services/xxx/yyy/zzz",
        "json": {
            "username": "Shiori Feed",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "ping",
                    },
                }
            ],
        },
    }


def test_get_rss_execution_setting_returns_200(client):
    resp = client.get("/settings/rss-execution")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


def test_set_rss_execution_setting_returns_200(client):
    resp = client.put("/settings/rss-execution", json={"enabled": True})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True

    resp = client.get("/settings/rss-execution")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True


def test_list_rss_feeds_returns_200(client):
    create_feed(client, url="https://a.example.com/feed", title="A")
    create_feed(client, url="https://b.example.com/feed", title="B")
    resp = client.get("/rss-feeds")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_get_rss_feed_returns_200(client):
    feed_id = create_feed(client).json()["id"]
    resp = client.get(f"/rss-feeds/{feed_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == feed_id


def test_update_rss_feed_returns_200(client):
    feed_id = create_feed(client, title="Old").json()["id"]
    resp = client.patch(f"/rss-feeds/{feed_id}", json={"title": "New"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"


def test_update_rss_feed_can_clear_description(client):
    feed_id = client.post(
        "/rss-feeds",
        json={
            "url": "https://example.com/feed.xml",
            "title": "Example",
            "description": "Original description",
        },
    ).json()["id"]

    resp = client.patch(f"/rss-feeds/{feed_id}", json={"description": None})

    assert resp.status_code == 200
    assert resp.json()["description"] is None


@pytest.mark.parametrize(
    "payload",
    [{"url": None}, {"title": None}, {"notify_webhook_enabled": None}],
)
def test_update_rss_feed_rejects_null_for_non_nullable_fields(client, payload):
    feed_id = create_feed(client).json()["id"]

    resp = client.patch(f"/rss-feeds/{feed_id}", json=payload)

    assert resp.status_code == 422


def test_update_rss_feed_can_disable_webhook_notification(client):
    feed_id = create_feed(client).json()["id"]
    resp = client.patch(
        f"/rss-feeds/{feed_id}", json={"notify_webhook_enabled": False}
    )
    assert resp.status_code == 200
    assert resp.json()["notify_webhook_enabled"] is False


def test_execute_rss_feed_still_sends_when_webhook_notification_disabled(client, monkeypatch):
    import api.services.webhook_service as webhook_module

    called = {}

    def fake_post(url, json, timeout=5.0):
        called["url"] = url
        called["json"] = json

        class Response:
            status_code = 204

        return Response()

    monkeypatch.setattr(webhook_module.httpx, "post", fake_post)
    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://hooks.slack.com/services/xxx/yyy/zzz"},
    )
    feed_id = client.post(
        "/rss-feeds",
        json={
            "url": "https://example.com/feed.xml",
            "title": "Example",
            "notify_webhook_enabled": False,
        },
    ).json()["id"]

    resp = client.post(f"/rss-feeds/{feed_id}/execute")
    assert resp.status_code == 200
    assert resp.json()["delivered"] is True
    assert resp.json()["message"] == "Posted 2 pending article(s)."
    assert called["url"] == "https://hooks.slack.com/services/xxx/yyy/zzz"
    assert called["json"]["blocks"][0]["type"] == "header"


def test_execute_rss_feed_returns_200(client):
    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://hooks.slack.com/services/xxx/yyy/zzz"},
    )
    feed_id = client.post(
        "/rss-feeds",
        json={"url": "https://example.com/feed.xml", "title": "Example"},
    ).json()["id"]
    resp = client.post(f"/rss-feeds/{feed_id}/execute")
    assert resp.status_code == 200
    assert resp.json()["feed_id"] == feed_id
    assert resp.json()["delivered"] is True


def test_list_rss_feed_articles_returns_200(client):
    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    )
    feed_id = create_feed(client).json()["id"]
    client.post(f"/rss-feeds/{feed_id}/execute")

    resp = client.get(f"/rss-feeds/{feed_id}/articles")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["items"][0]["feed_id"] == feed_id
    assert body["items"][0]["url"].startswith("https://example.com/item-")


def test_execute_rss_feed_preserves_source_timezone_offset(client, monkeypatch):
    import api.services.rss_feed_service as rss_module

    feed_id = create_feed(client).json()["id"]

    class ParsedEntry:
        def get(self, key, default=None):
            return {
                "title": "Tokyo article",
                "link": "https://example.com/tokyo-article",
                "published": "2026-08-04T14:30:00+09:00",
            }.get(key, default)

    class ParsedFeed:
        bozo = False
        feed = {"title": "Parsed Example"}
        entries = [ParsedEntry()]

    monkeypatch.setattr(rss_module.feedparser, "parse", lambda content: ParsedFeed())

    execute = client.post(f"/rss-feeds/{feed_id}/execute")
    assert execute.status_code == 200

    response = client.get(f"/rss-feeds/{feed_id}/articles")
    assert response.status_code == 200
    assert response.json()["items"][0]["published"].isoformat() == (
        "2026-08-04T14:30:00+09:00"
    )


def test_list_rss_feed_articles_orders_by_published_desc(client, monkeypatch):
    import api.services.rss_feed_service as rss_module

    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    )
    feed_id = create_feed(client).json()["id"]

    class ParsedEntry:
        def __init__(self, title, link, published):
            self._title = title
            self._link = link
            self._published = published

        def get(self, key, default=None):
            data = {
                "title": self._title,
                "link": self._link,
                "pubDate": self._published,
            }
            return data.get(key, default)

    class ParsedFeed:
        bozo = False
        feed = {"title": "Parsed Example"}
        entries = [
            ParsedEntry("Item 1", "https://example.com/item-1", "Wed, 01 Jan 2025 00:00:00 GMT"),
            ParsedEntry("Item 2", "https://example.com/item-2", "Fri, 03 Jan 2025 00:00:00 GMT"),
            ParsedEntry("Item 3", "https://example.com/item-3", "Thu, 02 Jan 2025 00:00:00 GMT"),
        ]

    def fake_get(url, timeout=5.0, follow_redirects=True):
        class Response:
            status_code = 200
            content = b"feed"

        return Response()

    monkeypatch.setattr(rss_module.httpx, "get", fake_get)
    monkeypatch.setattr(rss_module.feedparser, "parse", lambda content: ParsedFeed())

    execute = client.post(f"/rss-feeds/{feed_id}/execute")
    assert execute.status_code == 200

    resp = client.get(f"/rss-feeds/{feed_id}/articles")
    assert resp.status_code == 200
    body = resp.json()
    assert [item["url"] for item in body["items"]] == [
        "https://example.com/item-2",
        "https://example.com/item-3",
        "https://example.com/item-1",
    ]


def test_list_rss_feed_articles_orders_batch_rfc_dates_by_instant(client):
    import api.services.rss_feed_service as rss_module

    feed_id = create_feed(client).json()["id"]
    with rss_module.get_db() as conn:
        conn.executemany(
            """
            INSERT INTO rss_feed_articles (feed_id, url, title, published)
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    feed_id,
                    "https://example.com/item-1",
                    "Item 1",
                    "Wed, 01 Jan 2025 00:00:00 GMT",
                ),
                (
                    feed_id,
                    "https://example.com/item-2",
                    "Item 2",
                    "Fri, 03 Jan 2025 00:00:00 GMT",
                ),
                (
                    feed_id,
                    "https://example.com/item-3",
                    "Item 3",
                    "Thu, 02 Jan 2025 00:00:00 GMT",
                ),
                (feed_id, "https://example.com/item-undated", "Undated", None),
            ],
        )

    resp = client.get(f"/rss-feeds/{feed_id}/articles")

    assert resp.status_code == 200
    assert [item["url"] for item in resp.json()["items"]] == [
        "https://example.com/item-2",
        "https://example.com/item-3",
        "https://example.com/item-1",
        "https://example.com/item-undated",
    ]


def test_list_rss_feed_articles_accepts_page_and_per_page(client, monkeypatch):
    import api.services.rss_feed_service as rss_module

    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    )
    feed_id = create_feed(client).json()["id"]

    class ParsedEntry:
        def __init__(self, index):
            self._index = index

        def get(self, key, default=None):
            data = {
                "title": f"Item {self._index}",
                "link": f"https://example.com/item-{self._index}",
            }
            return data.get(key, default)

    class ParsedFeed:
        bozo = False
        feed = {"title": "Parsed Example"}
        entries = [ParsedEntry(index) for index in range(1, 6)]

    def fake_get(url, timeout=5.0, follow_redirects=True):
        class Response:
            status_code = 200
            content = b"feed"

        return Response()

    monkeypatch.setattr(rss_module.httpx, "get", fake_get)
    monkeypatch.setattr(rss_module.feedparser, "parse", lambda content: ParsedFeed())

    execute = client.post(f"/rss-feeds/{feed_id}/execute")
    assert execute.status_code == 200

    resp = client.get(f"/rss-feeds/{feed_id}/articles?page=2&per_page=2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 2
    assert body["per_page"] == 2
    assert body["total"] == 5
    assert body["total_pages"] == 3
    assert len(body["items"]) == 2


def test_list_rss_feed_articles_filters_by_published_date_range(client, monkeypatch):
    import api.services.rss_feed_service as rss_module

    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    )
    feed_id = create_feed(client).json()["id"]

    class ParsedEntry:
        def __init__(self, title, link, published):
            self._title = title
            self._link = link
            self._published = published

        def get(self, key, default=None):
            data = {
                "title": self._title,
                "link": self._link,
                "pubDate": self._published,
            }
            return data.get(key, default)

    class ParsedFeed:
        bozo = False
        feed = {"title": "Parsed Example"}
        entries = [
            ParsedEntry("Item 1", "https://example.com/item-1", "Mon, 06 Jan 2025 00:00:00 GMT"),
            ParsedEntry("Item 2", "https://example.com/item-2", "Tue, 07 Jan 2025 00:00:00 GMT"),
            ParsedEntry("Item 3", "https://example.com/item-3", "Wed, 08 Jan 2025 00:00:00 GMT"),
        ]

    def fake_get(url, timeout=5.0, follow_redirects=True):
        class Response:
            status_code = 200
            content = b"feed"

        return Response()

    monkeypatch.setattr(rss_module.httpx, "get", fake_get)
    monkeypatch.setattr(rss_module.feedparser, "parse", lambda content: ParsedFeed())

    execute = client.post(f"/rss-feeds/{feed_id}/execute")
    assert execute.status_code == 200

    resp = client.get(f"/rss-feeds/{feed_id}/articles?published_from=2025-01-07&published_to=2025-01-08")
    assert resp.status_code == 200
    body = resp.json()
    assert [item["url"] for item in body["items"]] == [
        "https://example.com/item-3",
        "https://example.com/item-2",
    ]
    assert body["total"] == 2


def test_list_rss_feed_articles_filters_by_title_query(client, monkeypatch):
    import api.services.rss_feed_service as rss_module

    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    )
    feed_id = create_feed(client).json()["id"]

    class ParsedEntry:
        def __init__(self, title, link, published):
            self._title = title
            self._link = link
            self._published = published

        def get(self, key, default=None):
            data = {
                "title": self._title,
                "link": self._link,
                "pubDate": self._published,
            }
            return data.get(key, default)

    class ParsedFeed:
        bozo = False
        feed = {"title": "Parsed Example"}
        entries = [
            ParsedEntry("Alpha One", "https://example.com/alpha-1", "Mon, 06 Jan 2025 00:00:00 GMT"),
            ParsedEntry("Beta Two", "https://example.com/beta-2", "Tue, 07 Jan 2025 00:00:00 GMT"),
            ParsedEntry("Alpha Three", "https://example.com/alpha-3", "Wed, 08 Jan 2025 00:00:00 GMT"),
        ]

    def fake_get(url, timeout=5.0, follow_redirects=True):
        class Response:
            status_code = 200
            content = b"feed"

        return Response()

    monkeypatch.setattr(rss_module.httpx, "get", fake_get)
    monkeypatch.setattr(rss_module.feedparser, "parse", lambda content: ParsedFeed())

    execute = client.post(f"/rss-feeds/{feed_id}/execute")
    assert execute.status_code == 200

    resp = client.get(f"/rss-feeds/{feed_id}/articles?q=alpha")
    assert resp.status_code == 200
    body = resp.json()
    assert [item["url"] for item in body["items"]] == [
        "https://example.com/alpha-3",
        "https://example.com/alpha-1",
    ]
    assert body["total"] == 2


def test_list_rss_feed_articles_returns_404_for_missing_feed(client):
    resp = client.get("/rss-feeds/99999/articles")
    assert resp.status_code == 404


def test_execute_rss_feed_uses_feedparser_content(client, monkeypatch):
    import api.services.rss_feed_service as rss_module

    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    )
    feed_id = create_feed(
        client, url="https://example.com/feed.xml", title="Example"
    ).json()["id"]

    captured = {}

    def fake_post(url, json, timeout=5.0):
        captured["json"] = json

        class Response:
            status_code = 204

        return Response()

    class ParsedEntry:
        def __init__(self, title, link):
            self._title = title
            self._link = link

        def get(self, key, default=None):
            data = {
                "title": self._title,
                "link": self._link,
            }
            return data.get(key, default)

    class ParsedFeed:
        bozo = False
        feed = {"title": "Parsed Example"}
        entries = [
            ParsedEntry("Item 1", "https://example.com/item-1"),
            ParsedEntry("Item 2", "https://example.com/item-2"),
        ]

    def fake_get(url, timeout=5.0, follow_redirects=True):
        class Response:
            status_code = 200
            content = b"<?xml version='1.0'?><rss><channel><title>Parsed Example</title><item><title>Item 1</title><link>https://example.com/item-1</link></item></channel></rss>"

        return Response()

    monkeypatch.setattr(rss_module.httpx, "get", fake_get)
    monkeypatch.setattr(rss_module.httpx, "post", fake_post)
    monkeypatch.setattr(rss_module.feedparser, "parse", lambda content: ParsedFeed())

    resp = client.post(f"/rss-feeds/{feed_id}/execute")
    assert resp.status_code == 200
    assert captured["json"]["content"] == (
        "**Parsed Example** - **New articles** (2 items)"
    )
    assert captured["json"]["username"] == "Shiori Feed"
    assert captured["json"]["embeds"] == [
        {
            "title": "Item 1",
            "url": "https://example.com/item-1",
        },
        {
            "title": "Item 2",
            "url": "https://example.com/item-2",
        },
    ]


def test_execute_rss_feed_splits_embeds_into_batches(client, monkeypatch):
    import api.services.rss_feed_service as rss_module

    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    )
    feed_id = create_feed(
        client, url="https://example.com/feed.xml", title="Example"
    ).json()["id"]

    payloads = []

    def fake_post(url, json, timeout=5.0):
        payloads.append(json)

        class Response:
            status_code = 204

        return Response()

    class ParsedEntry:
        def __init__(self, index):
            self._index = index

        def get(self, key, default=None):
            data = {
                "title": f"Item {self._index}",
                "link": f"https://example.com/item-{self._index}",
            }
            return data.get(key, default)

    class ParsedFeed:
        bozo = False
        feed = {"title": "Parsed Example"}
        entries = [ParsedEntry(index) for index in range(1, 13)]

    def fake_get(url, timeout=5.0, follow_redirects=True):
        class Response:
            status_code = 200
            content = b"feed"

        return Response()

    monkeypatch.setattr(rss_module.httpx, "get", fake_get)
    monkeypatch.setattr(rss_module.httpx, "post", fake_post)
    monkeypatch.setattr(rss_module.feedparser, "parse", lambda content: ParsedFeed())

    resp = client.post(f"/rss-feeds/{feed_id}/execute")
    assert resp.status_code == 200
    assert len(payloads) == 2
    assert len(payloads[0]["embeds"]) == 10
    assert len(payloads[1]["embeds"]) == 2
    assert payloads[1]["content"] == (
        "**Parsed Example** - **New articles** (12 items) [2]"
    )


def test_execute_rss_feed_returns_discord_error_detail(client, monkeypatch):
    import api.services.webhook_service as webhook_module

    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    )
    feed_id = create_feed(
        client, url="https://example.com/feed.xml", title="Example"
    ).json()["id"]

    def fake_post(url, json, timeout=5.0):
        class Response:
            status_code = 400
            headers = {"content-type": "application/json"}

            def json(self):
                return {"message": "Invalid payload provided"}

            @property
            def text(self):
                return '{"message":"Invalid payload provided"}'

        return Response()

    monkeypatch.setattr(webhook_module.httpx, "post", fake_post)

    resp = client.post(f"/rss-feeds/{feed_id}/execute")
    assert resp.status_code == 502
    assert resp.json()["detail"] == "Failed to notify webhook"


def test_execute_rss_feed_keeps_articles_pending_when_webhook_fails(client, monkeypatch):
    import api.services.webhook_service as webhook_module

    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    )
    feed_id = create_feed(
        client, url="https://example.com/feed.xml", title="Example"
    ).json()["id"]

    def fake_post(url, json, timeout=5.0):
        class Response:
            status_code = 500
            headers = {"content-type": "application/json"}

            def json(self):
                return {"message": "Invalid payload provided"}

            @property
            def text(self):
                return '{"message":"Invalid payload provided"}'

        return Response()

    monkeypatch.setattr(webhook_module.httpx, "post", fake_post)

    resp = client.post(f"/rss-feeds/{feed_id}/execute")
    assert resp.status_code == 502

    articles_resp = client.get(f"/rss-feeds/{feed_id}/articles")
    assert articles_resp.status_code == 200
    assert articles_resp.json()["items"]
    assert all(not item["webhook_notified"] for item in articles_resp.json()["items"])


def test_execute_rss_feed_skips_already_sent_articles(client, monkeypatch):
    import api.services.rss_feed_service as rss_module
    import api.services.webhook_service as webhook_module

    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    )
    feed_id = create_feed(
        client, url="https://example.com/feed.xml", title="Example"
    ).json()["id"]

    payloads = []

    def fake_post(url, json, timeout=5.0):
        payloads.append(json)

        class Response:
            status_code = 204

        return Response()

    class ParsedEntry:
        def __init__(self, title, link):
            self._title = title
            self._link = link

        def get(self, key, default=None):
            data = {"title": self._title, "link": self._link}
            return data.get(key, default)

    class ParsedFeed:
        bozo = False
        feed = {"title": "Parsed Example"}
        entries = [ParsedEntry("Item 1", "https://example.com/item-1")]

    def fake_get(url, timeout=5.0, follow_redirects=True):
        class Response:
            status_code = 200
            content = b"feed"

        return Response()

    monkeypatch.setattr(rss_module.httpx, "get", fake_get)
    monkeypatch.setattr(webhook_module.httpx, "post", fake_post)
    monkeypatch.setattr(rss_module.feedparser, "parse", lambda content: ParsedFeed())

    first = client.post(f"/rss-feeds/{feed_id}/execute")
    second = client.post(f"/rss-feeds/{feed_id}/execute")

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(payloads) == 1


def test_execute_rss_feed_returns_message_when_no_new_articles(client, monkeypatch):
    import api.services.rss_feed_service as rss_module

    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    )
    feed_id = create_feed(
        client, url="https://example.com/feed.xml", title="Example"
    ).json()["id"]

    payloads = []

    def fake_post(url, json, timeout=5.0):
        payloads.append(json)

        class Response:
            status_code = 204

        return Response()

    class ParsedFeed:
        bozo = False
        feed = {"title": "Parsed Example"}
        entries = [
            type(
                "ParsedEntry",
                (),
                {
                    "get": lambda self, key, default=None: {
                        "title": "Item 1",
                        "link": "https://example.com/item-1",
                    }.get(key, default)
                },
            )()
        ]

    def fake_get(url, timeout=5.0, follow_redirects=True):
        class Response:
            status_code = 200
            content = b"feed"

        return Response()

    monkeypatch.setattr(rss_module.httpx, "get", fake_get)
    monkeypatch.setattr(rss_module.httpx, "post", fake_post)
    monkeypatch.setattr(rss_module.feedparser, "parse", lambda content: ParsedFeed())

    first = client.post(f"/rss-feeds/{feed_id}/execute")
    second = client.post(f"/rss-feeds/{feed_id}/execute")

    assert first.status_code == 200
    assert first.json()["message"] == "Posted 1 pending article(s)."
    assert second.status_code == 200
    assert second.json()["message"] == "No new articles found."
    assert len(payloads) == 1


def test_create_rss_feed_with_webhook_selection(client):
    webhook = client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    ).json()
    resp = client.post(
        "/rss-feeds",
        json={
            "url": "https://example.com/feed.xml",
            "title": "Example",
            "webhook_ids": [webhook["id"]],
        },
    )
    assert resp.status_code == 201
    assert resp.json()["webhook_ids"] == [webhook["id"]]


def test_create_rss_feed_without_webhook_selection_returns_empty_ids(client):
    resp = create_feed(client)
    assert resp.status_code == 201
    assert resp.json()["webhook_ids"] == []


def test_create_rss_feed_with_unknown_webhook_id_returns_404(client):
    resp = client.post(
        "/rss-feeds",
        json={
            "url": "https://example.com/feed.xml",
            "title": "Example",
            "webhook_ids": [99999],
        },
    )
    assert resp.status_code == 404


def test_create_rss_feed_with_duplicate_webhook_ids_returns_422(client):
    resp = client.post(
        "/rss-feeds",
        json={
            "url": "https://example.com/feed.xml",
            "title": "Example",
            "webhook_ids": [1, 1],
        },
    )
    assert resp.status_code == 422


def test_update_rss_feed_webhook_selection(client):
    first = client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    ).json()
    second = client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://hooks.slack.com/services/xxx/yyy/zzz"},
    ).json()
    feed_id = create_feed(client).json()["id"]

    resp = client.patch(
        f"/rss-feeds/{feed_id}", json={"webhook_ids": [first["id"], second["id"]]}
    )
    assert resp.status_code == 200
    assert resp.json()["webhook_ids"] == [first["id"], second["id"]]

    listed = client.get("/rss-feeds").json()
    assert listed["items"][0]["webhook_ids"] == [first["id"], second["id"]]

    cleared = client.patch(f"/rss-feeds/{feed_id}", json={"webhook_ids": []})
    assert cleared.status_code == 200
    assert cleared.json()["webhook_ids"] == []


def test_update_rss_feed_with_null_webhook_ids_returns_422(client):
    feed_id = create_feed(client).json()["id"]
    resp = client.patch(f"/rss-feeds/{feed_id}", json={"webhook_ids": None})
    assert resp.status_code == 422


def test_execute_rss_feed_notifies_only_selected_webhooks(client, monkeypatch):
    import api.services.webhook_service as webhook_module

    notified_urls = []

    def fake_post(url, json, timeout=5.0):
        notified_urls.append(url)

        class Response:
            status_code = 204

        return Response()

    monkeypatch.setattr(webhook_module.httpx, "post", fake_post)
    discord = client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    ).json()
    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://hooks.slack.com/services/xxx/yyy/zzz"},
    )
    resp = client.post(
        "/rss-feeds",
        json={
            "url": "https://example.com/feed.xml",
            "title": "Example",
            "webhook_ids": [discord["id"]],
        },
    )
    feed_id = resp.json()["id"]

    resp = client.post(f"/rss-feeds/{feed_id}/execute")

    assert resp.status_code == 200
    assert resp.json()["delivered_count"] == 1
    assert notified_urls == ["https://discord.com/api/webhooks/1/token"]


def test_execute_rss_feed_without_webhook_saves_and_later_notifies_pending_articles(
    client, monkeypatch
):
    import api.services.webhook_service as webhook_module

    feed_id = create_feed(client).json()["id"]
    resp = client.post(f"/rss-feeds/{feed_id}/execute")
    assert resp.status_code == 200
    assert resp.json()["delivered"] is False
    assert resp.json()["delivered_count"] == 0
    articles = client.get(f"/rss-feeds/{feed_id}/articles").json()["items"]
    assert articles
    assert all(not item["webhook_notified"] for item in articles)

    delivered_payloads = []

    def fake_post(url, json, timeout=5.0):
        delivered_payloads.append(json)

        class Response:
            status_code = 204

        return Response()

    monkeypatch.setattr(webhook_module.httpx, "post", fake_post)
    client.post(
        "/settings/webhooks",
        json={"name": "Later", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    )
    notified = client.post(f"/rss-feeds/{feed_id}/execute")

    assert notified.status_code == 200
    assert notified.json()["delivered_count"] == 1
    assert len(delivered_payloads) == 1
    articles = client.get(f"/rss-feeds/{feed_id}/articles").json()["items"]
    assert all(item["webhook_notified"] for item in articles)


def test_execute_rss_feed_leaves_articles_over_webhook_limit_pending(client):
    client.put("/settings/webhook-article-limit", json={"max_articles": 1})
    client.post(
        "/settings/webhooks",
        json={
            "name": "Limited",
            "webhook_url": "https://discord.com/api/webhooks/1/token",
        },
    )
    feed_id = create_feed(client).json()["id"]

    first = client.post(f"/rss-feeds/{feed_id}/execute")
    first_articles = client.get(f"/rss-feeds/{feed_id}/articles").json()["items"]

    assert first.status_code == 200
    assert first.json()["message"] == "Posted 1 pending article(s)."
    assert sum(item["webhook_notified"] for item in first_articles) == 1

    second = client.post(f"/rss-feeds/{feed_id}/execute")
    second_articles = client.get(f"/rss-feeds/{feed_id}/articles").json()["items"]

    assert second.json()["message"] == "Posted 1 pending article(s)."
    assert all(item["webhook_notified"] for item in second_articles)


def test_execute_rss_feed_delivers_to_all_registered_webhooks(client, monkeypatch):
    import api.services.webhook_service as webhook_module

    notified_urls = []

    def fake_post(url, json, timeout=5.0):
        notified_urls.append(url)

        class Response:
            status_code = 204

        return Response()

    monkeypatch.setattr(webhook_module.httpx, "post", fake_post)
    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    )
    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://hooks.slack.com/services/xxx/yyy/zzz"},
    )
    feed_id = create_feed(client).json()["id"]

    resp = client.post(f"/rss-feeds/{feed_id}/execute")

    assert resp.status_code == 200
    assert resp.json()["delivered"] is True
    assert resp.json()["delivered_count"] == 2
    assert notified_urls == [
        "https://discord.com/api/webhooks/1/token",
        "https://hooks.slack.com/services/xxx/yyy/zzz",
    ]


def test_execute_rss_feed_skips_disabled_webhooks(client, monkeypatch):
    import api.services.webhook_service as webhook_module

    notified_urls = []

    def fake_post(url, json, timeout=5.0):
        notified_urls.append(url)

        class Response:
            status_code = 204

        return Response()

    monkeypatch.setattr(webhook_module.httpx, "post", fake_post)
    disabled = client.post(
        "/settings/webhooks",
        json={"name": "Discord", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    ).json()
    client.patch(f"/settings/webhooks/{disabled['id']}", json={"enabled": False})
    client.post(
        "/settings/webhooks",
        json={"name": "Slack", "webhook_url": "https://hooks.slack.com/services/xxx/yyy/zzz"},
    )
    feed_id = create_feed(client).json()["id"]

    resp = client.post(f"/rss-feeds/{feed_id}/execute")

    assert resp.status_code == 200
    assert resp.json()["delivered_count"] == 1
    assert notified_urls == ["https://hooks.slack.com/services/xxx/yyy/zzz"]


def test_execute_rss_feed_succeeds_when_one_webhook_fails(client, monkeypatch):
    import api.services.webhook_service as webhook_module

    def fake_post(url, json, timeout=5.0):
        class Response:
            status_code = 500 if "discord" in url else 204

        return Response()

    monkeypatch.setattr(webhook_module.httpx, "post", fake_post)
    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    )
    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://hooks.slack.com/services/xxx/yyy/zzz"},
    )
    feed_id = create_feed(client).json()["id"]

    resp = client.post(f"/rss-feeds/{feed_id}/execute")

    assert resp.status_code == 200
    assert resp.json()["delivered"] is True
    assert resp.json()["delivered_count"] == 1


def test_execute_rss_feed_returns_502_when_all_webhooks_fail(client, monkeypatch):
    import api.services.webhook_service as webhook_module

    def fake_post(url, json, timeout=5.0):
        class Response:
            status_code = 500
            headers = {"content-type": "application/json"}

            def json(self):
                return {"message": "Invalid payload provided"}

            @property
            def text(self):
                return '{"message":"Invalid payload provided"}'

        return Response()

    monkeypatch.setattr(webhook_module.httpx, "post", fake_post)
    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    )
    client.post(
        "/settings/webhooks",
        json={"name": "Test webhook", "webhook_url": "https://hooks.slack.com/services/xxx/yyy/zzz"},
    )
    feed_id = create_feed(client).json()["id"]

    resp = client.post(f"/rss-feeds/{feed_id}/execute")

    assert resp.status_code == 502
    assert resp.json()["detail"] == "Failed to notify webhook"


def test_delete_rss_feed_returns_204(client):
    feed_id = create_feed(client).json()["id"]
    resp = client.delete(f"/rss-feeds/{feed_id}")
    assert resp.status_code == 204


def test_create_rss_feed_with_duplicate_url_returns_409(client):
    create_feed(client)
    resp = create_feed(client)
    assert resp.status_code == 409


def test_create_rss_feed_with_invalid_url_returns_422(client):
    resp = client.post("/rss-feeds", json={"url": "not-a-url", "title": "Test"})
    assert resp.status_code == 422


def test_register_webhook_with_non_discord_webhook_returns_422(client):
    resp = client.post(
        "/settings/webhooks", json={"name": "Test webhook", "webhook_url": "https://example.com/webhook"}
    )
    assert resp.status_code == 422


def test_ping_webhook_with_non_discord_url_returns_422(client):
    resp = client.post(
        "/settings/webhook/ping", json={"name": "Test webhook", "webhook_url": "https://example.com/webhook"}
    )
    assert resp.status_code == 422


def test_ping_webhook_with_invalid_url_returns_422(client):
    resp = client.post("/settings/webhook/ping", json={"name": "Test webhook", "webhook_url": "not-a-url"})
    assert resp.status_code == 422


def test_ping_webhook_when_discord_returns_error_returns_502(client, monkeypatch):
    import api.services.settings_service as settings_module

    def fake_post(url, json, timeout=5.0):
        class Response:
            status_code = 500

        return Response()

    monkeypatch.setattr(settings_module.httpx, "post", fake_post)

    resp = client.post(
        "/settings/webhook/ping",
        json={"name": "Test webhook", "webhook_url": "https://discord.com/api/webhooks/1/token"},
    )
    assert resp.status_code == 502


def test_create_rss_feed_with_empty_title_returns_422(client):
    resp = client.post(
        "/rss-feeds", json={"url": "https://example.com/feed", "title": "   "}
    )
    assert resp.status_code == 422


def test_create_rss_feed_with_non_feed_url_returns_422(client, monkeypatch):
    import api.services.rss_feed_service as rss_module

    def fake_get(url, timeout=5.0, follow_redirects=True):
        class Response:
            status_code = 200
            text = "<html><body>Not a feed</body></html>"

        return Response()

    monkeypatch.setattr(rss_module.httpx, "get", fake_get)

    resp = create_feed(client, url="https://example.com/not-a-feed.xml")
    assert resp.status_code == 422


def test_get_nonexistent_rss_feed_returns_404(client):
    resp = client.get("/rss-feeds/99999")
    assert resp.status_code == 404

def test_validation_exception_handler_serializes_field_validator_errors():
    """Field validator errors must serialize into a 422 JSON response, not a 500."""
    import anyio
    from fastapi.exceptions import RequestValidationError
    from pydantic import ValidationError

    from api.main import validation_exception_handler
    from api.model.models import RSSFeedCreate

    with pytest.raises(ValidationError) as exc_info:
        RSSFeedCreate.model_validate(
            {"url": "https://example.com/feed.xml", "title": "   "}
        )

    response = anyio.run(
        validation_exception_handler,
        None,
        RequestValidationError(exc_info.value.errors()),
    )
    assert response.status_code == 422
    assert b"Title cannot be empty" in response.body
