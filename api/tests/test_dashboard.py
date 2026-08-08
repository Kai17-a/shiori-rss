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

    import api.services.dashboard_service as dashboard_module

    @contextmanager
    def patched_get_db(database_url=db_path):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    monkeypatch.setattr(dashboard_module, "get_db", patched_get_db)
    with patched_get_db() as conn:
        conn.execute(
            "INSERT INTO rss_feeds (id, url, title) VALUES (1, ?, ?)",
            ("https://example.com/feed.xml", "Daily RSS"),
        )
        conn.execute(
            """
            INSERT INTO news_sites (id, url, title, scrape_config)
            VALUES (1, ?, ?, '{}')
            """,
            ("https://example.com/news", "Custom Daily"),
        )
        conn.execute(
            """
            INSERT INTO rss_feed_articles
                (feed_id, url, title, summary, published, webhook_notified)
            VALUES (1, ?, ?, ?, ?, 1)
            """,
            (
                "https://example.com/rss-today",
                "RSS today",
                "RSS summary",
                "2026-08-08 09:00:00",
            ),
        )
        conn.execute(
            """
            INSERT INTO news_site_articles
                (site_id, url, title, summary, published, webhook_notified)
            VALUES (1, ?, ?, ?, ?, 0)
            """,
            (
                "https://example.com/custom-today",
                "Custom today",
                "Custom summary",
                "2026-08-08 10:00:00",
            ),
        )
        conn.execute(
            """
            INSERT INTO rss_feed_articles
                (feed_id, url, title, published, webhook_notified)
            VALUES (1, ?, ?, ?, 0)
            """,
            ("https://example.com/yesterday", "Yesterday", "2026-08-07 10:00:00"),
        )

    with TestClient(app) as test_client:
        yield test_client


def test_dashboard_summarizes_sources_and_articles_for_access_date(client):
    response = client.get("/dashboard?date=2026-08-08")

    assert response.status_code == 200
    assert response.json()["summary"] == {
        "rss_feed_count": 1,
        "custom_feed_count": 1,
        "today_article_count": 2,
        "pending_notification_count": 2,
    }
    assert [article["title"] for article in response.json()["articles"]] == [
        "Custom today",
        "RSS today",
    ]
    assert response.json()["articles"][0]["source_type"] == "custom"


def test_dashboard_rejects_missing_access_date(client):
    response = client.get("/dashboard")

    assert response.status_code == 422
