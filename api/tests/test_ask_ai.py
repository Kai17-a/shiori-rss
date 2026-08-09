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

    import api.services.ask_ai_service as ask_ai_module

    monkeypatch.setattr(ask_ai_module, "get_db", patched_get_db)
    with patched_get_db() as conn:
        conn.execute(
            "INSERT INTO rss_feeds (id, url, title) VALUES (1, ?, ?)",
            ("https://example.com/feed.xml", "Tech Feed"),
        )
        conn.execute(
            """
            INSERT INTO rss_feed_articles
                (feed_id, url, title, summary, published)
            VALUES (1, ?, ?, ?, ?)
            """,
            (
                "https://example.com/agent",
                "Agentic AI systems",
                "A practical guide to building autonomous AI agents.",
                "2026-08-09T08:00:00+00:00",
            ),
        )
        for key, value in (
            ("llm_provider", "openai"),
            ("llm_base_url", "https://llm.example.com/v1"),
            ("llm_model", "example-model"),
        ):
            conn.execute(
                "INSERT INTO app_settings (key, value) VALUES (?, ?)",
                (key, value),
            )

    replies = iter(
        [
            '{"keywords":["人工知能に関する記事"],"source_types":[],"published_after":null,"published_before":null}',
            "The saved article describes autonomous agent systems. [S1]",
        ]
    )
    monkeypatch.setattr(
        ask_ai_module, "chat_completion", lambda *args, **kwargs: next(replies)
    )
    with TestClient(app) as test_client:
        yield test_client


def test_ask_ai_searches_saved_articles_and_returns_sources(client):
    response = client.post(
        "/ai/chat", json={"message": "AIに関する記事一覧を10件出して"}
    )

    assert response.status_code == 200
    assert response.json()["answer"].endswith("[S1]")
    assert response.json()["sources"][0]["title"] == "Agentic AI systems"
    assert response.json()["sources"][0]["source_type"] == "rss"


def test_ask_ai_rejects_empty_questions(client):
    response = client.post("/ai/chat", json={"message": "  "})

    assert response.status_code == 422


def test_article_search_index_tracks_article_deletion(tmp_path):
    db_path = str(tmp_path / "trigger.db")
    build_test_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO rss_feeds (id, url, title) VALUES (1, ?, ?)",
            ("https://example.com/feed.xml", "Tech Feed"),
        )
        cursor = conn.execute(
            "INSERT INTO rss_feed_articles (feed_id, url, title) VALUES (1, ?, ?)",
            ("https://example.com/article", "Searchable article"),
        )
        assert (
            conn.execute(
                "SELECT count(*) FROM article_search WHERE article_search MATCH ?",
                ("Searchable",),
            ).fetchone()[0]
            == 1
        )

        conn.execute("DELETE FROM rss_feed_articles WHERE id = ?", (cursor.lastrowid,))
        assert (
            conn.execute(
                "SELECT count(*) FROM article_search WHERE article_search MATCH ?",
                ("Searchable",),
            ).fetchone()[0]
            == 0
        )


def test_ask_ai_removes_date_filter_after_relaxed_search_finds_nothing(
    tmp_path, monkeypatch
):
    db_path = str(tmp_path / "date-fallback.db")
    build_test_db(db_path)

    @contextmanager
    def patched_get_db(database_url=db_path):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    import api.services.ask_ai_service as ask_ai_module

    monkeypatch.setattr(ask_ai_module, "get_db", patched_get_db)
    with patched_get_db() as conn:
        conn.execute(
            "INSERT INTO rss_feeds (id, url, title) VALUES (1, ?, ?)",
            ("https://example.com/feed.xml", "Tech Feed"),
        )
        conn.execute(
            """
            INSERT INTO rss_feed_articles (feed_id, url, title, published)
            VALUES (1, ?, ?, ?)
            """,
            (
                "https://example.com/older-ai",
                "AI systems",
                "2026-08-01T08:00:00+00:00",
            ),
        )
        for key, value in (
            ("llm_provider", "openai"),
            ("llm_base_url", "https://llm.example.com/v1"),
            ("llm_model", "example-model"),
        ):
            conn.execute(
                "INSERT INTO app_settings (key, value) VALUES (?, ?)", (key, value)
            )

    replies = iter(
        [
            '{"keywords":["AI"],"source_types":[],"published_after":"2026-08-09T00:00:00Z","published_before":null}',
            "An older saved article covers AI systems. [S1]",
        ]
    )
    monkeypatch.setattr(
        ask_ai_module, "chat_completion", lambda *args, **kwargs: next(replies)
    )

    response = ask_ai_module.AskAIService().ask("今日のAI記事を教えて")

    assert response.sources[0].title == "AI systems"
