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

    import api.services.article_service as article_service_module

    @contextmanager
    def patched_get_db(database_url=db_path):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    monkeypatch.setattr(article_service_module, "get_db", patched_get_db)
    with patched_get_db() as conn:
        conn.execute(
            "INSERT INTO rss_feeds (id, url, title) VALUES (1, ?, ?)",
            ("https://example.com/feed.xml", "Daily RSS"),
        )
        conn.execute(
            "INSERT INTO rss_feeds (id, url, title) VALUES (2, ?, ?)",
            ("https://example.com/other-feed.xml", "Other RSS"),
        )
        conn.execute(
            "INSERT INTO news_sites (id, url, title, scrape_config) VALUES (1, ?, ?, '{}')",
            ("https://example.com/news", "Custom Daily"),
        )
        conn.execute(
            """
            INSERT INTO rss_feed_articles (feed_id, url, title, published, webhook_notified)
            VALUES (1, ?, ?, ?, 1)
            """,
            ("https://example.com/a1", "Rocket launch update", "2026-08-08T09:00:00+00:00"),
        )
        conn.execute(
            """
            INSERT INTO rss_feed_articles (feed_id, url, title, published, webhook_notified)
            VALUES (2, ?, ?, ?, 0)
            """,
            ("https://example.com/a2", "Weather report", "2026-08-07T09:00:00+00:00"),
        )
        conn.execute(
            """
            INSERT INTO news_site_articles (site_id, url, title, published, webhook_notified)
            VALUES (1, ?, ?, ?, 0)
            """,
            ("https://example.com/a3", "Custom rocket news", "2026-08-09T09:00:00+00:00"),
        )

    with TestClient(app) as test_client:
        yield test_client


def test_list_articles_returns_all_sources_ordered_by_recency(client):
    response = client.get("/articles")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert [item["title"] for item in payload["items"]] == [
        "Custom rocket news",
        "Rocket launch update",
        "Weather report",
    ]
    assert payload["items"][0]["source_type"] == "custom"
    assert payload["items"][0]["article_id"] == 1
    assert payload["items"][0]["source_id"] == 1


def test_list_articles_filters_by_search_text(client):
    response = client.get("/articles?q=rocket")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert {item["title"] for item in payload["items"]} == {
        "Custom rocket news",
        "Rocket launch update",
    }


def test_list_articles_filters_by_specific_source(client):
    response = client.get("/articles?source_type=rss&source_id=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["title"] == "Weather report"


def test_list_articles_filters_by_source_type_only(client):
    response = client.get("/articles?source_type=custom")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["source_type"] == "custom"


def test_list_articles_paginates(client):
    response = client.get("/articles?page=2&per_page=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 2
    assert payload["per_page"] == 2
    assert payload["total"] == 3
    assert payload["total_pages"] == 2
    assert len(payload["items"]) == 1


def test_list_articles_clamps_out_of_range_page_when_there_are_no_results(client):
    response = client.get("/articles?q=nonexistent&page=999")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 0
    assert payload["total_pages"] == 0
    assert payload["page"] == 1
    assert payload["items"] == []


def test_list_articles_escapes_sql_like_wildcards_in_search(client):
    response = client.get("/articles?q=%")

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_list_articles_rejects_source_id_without_source_type(client):
    response = client.get("/articles?source_id=1")

    assert response.status_code == 422


def test_list_articles_rejects_invalid_source_type(client):
    response = client.get("/articles?source_type=bogus")

    assert response.status_code == 422
