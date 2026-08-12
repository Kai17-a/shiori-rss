import json
import sqlite3
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.repositories.article_search_repo import ArticleSearchRepository
from api.services.ask_ai_service import AskAIService
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
            '{"references":["S1"]}',
            "The saved article describes autonomous agent systems. [S1]",
        ]
    )
    monkeypatch.setattr(
        ask_ai_module, "chat_completion", lambda *args, **kwargs: next(replies)
    )
    monkeypatch.setattr(
        ask_ai_module,
        "chat_completion_stream",
        lambda *args, **kwargs: iter(["Streamed ", "answer. [S1]"]),
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


def test_ask_ai_streams_sources_and_answer_deltas(client):
    import api.services.ask_ai_service as ask_ai_module

    events = [
        json.loads(line) for line in ask_ai_module.AskAIService().stream("AI news")
    ]

    assert [event["type"] for event in events] == [
        "delta",
        "delta",
        "sources",
        "done",
    ]
    assert events[2]["sources"][0]["reference"] == "S1"
    assert events[2]["sources"][0]["title"] == "Agentic AI systems"
    assert [event.get("delta") for event in events if event["type"] == "delta"] == [
        "Streamed ",
        "answer. [S1]",
    ]
    assert events[-1] == {"type": "done"}


def test_ask_ai_returns_only_sources_cited_by_the_answer():
    rows = [
        {
            "source_type": "rss",
            "article_id": article_id,
            "source_id": 1,
            "source_title": "Example feed",
            "title": title,
            "summary": None,
            "url": f"https://example.com/{article_id}",
            "published": None,
            "created_at": "2026-08-09T08:00:00+00:00",
        }
        for article_id, title in ((1, "Unrelated Svelte news"), (2, "OpenAI news"))
    ]

    sources = AskAIService._cited_sources("Relevant article. [S2]", rows)

    assert [(source.reference, source.title) for source in sources] == [
        ("S2", "OpenAI news")
    ]


def test_ask_ai_removes_unrelated_candidates_before_answering(monkeypatch):
    import api.services.ask_ai_service as ask_ai_module

    rows = [
        {
            "source_title": "Example feed",
            "title": title,
            "summary": summary,
        }
        for title, summary in (
            ("What’s new in Svelte", "Includes an incidental AI tool."),
            ("OpenAI launches a model", "A new OpenAI model was released."),
        )
    ]
    monkeypatch.setattr(
        ask_ai_module,
        "chat_completion",
        lambda *args, **kwargs: '{"references":["S2"]}',
    )

    selected = AskAIService()._select_relevant_rows(
        object(), "OpenAIのニュースを教えて", rows
    )

    assert [row["title"] for row in selected] == ["OpenAI launches a model"]


def test_ask_ai_keeps_explicit_article_list_topic_when_llm_returns_empty(monkeypatch):
    import api.services.ask_ai_service as ask_ai_module

    rows = [
        {
            "source_title": "さくらのクラウドニュース",
            "title": "IAMロール追加のお知らせ",
            "summary": "さくらのクラウドにIAMロールが追加されました。",
        },
        {
            "source_title": "Example feed",
            "title": "What’s new in Svelte",
            "summary": "A frontend framework update.",
        },
    ]
    monkeypatch.setattr(
        ask_ai_module,
        "chat_completion",
        lambda *args, **kwargs: '{"references":[]}',
    )

    selected = AskAIService()._select_relevant_rows(
        object(), "さくらのクラウドに関する記事を教えて", rows
    )

    assert [row["title"] for row in selected] == ["IAMロール追加のお知らせ"]


def test_ask_ai_does_not_force_short_broad_article_topics(monkeypatch):
    import api.services.ask_ai_service as ask_ai_module

    rows = [
        {
            "source_title": "Svelte",
            "title": "What’s new in Svelte",
            "summary": "Includes an incidental AI tool.",
        }
    ]
    monkeypatch.setattr(
        ask_ai_module,
        "chat_completion",
        lambda *args, **kwargs: '{"references":[]}',
    )

    selected = AskAIService()._select_relevant_rows(
        object(), "AIに関する記事を教えて", rows
    )

    assert selected == []


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


def test_article_search_uses_completed_ai_analysis_metadata(tmp_path):
    db_path = str(tmp_path / "analysis-search.db")
    build_test_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            "INSERT INTO rss_feeds (id, url, title) VALUES (1, ?, ?)",
            ("https://example.com/feed.xml", "Tech Feed"),
        )
        article_id = conn.execute(
            "INSERT INTO rss_feed_articles (feed_id, url, title) VALUES (1, ?, ?)",
            ("https://example.com/article", "A generic article"),
        ).lastrowid
        conn.execute(
            """
            INSERT INTO article_ai_analyses (
              source_type, article_id, content_hash, model, prompt_version,
              ai_summary, topics_json, status
            ) VALUES ('rss', ?, 'hash', 'model', 'v1', ?, ?, 'completed')
            """,
            (
                article_id,
                "Explains retrieval augmented generation patterns.",
                '["knowledge retrieval"]',
            ),
        )

        rows = ArticleSearchRepository(conn).search(
            keywords=["retrieval"],
            source_types=[],
            published_after=None,
            published_before=None,
            limit=10,
        )

        assert len(rows) == 1
        assert rows[0]["article_id"] == article_id
        assert rows[0]["ai_summary"].startswith("Explains retrieval")


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
            '{"references":["S1"]}',
            "An older saved article covers AI systems. [S1]",
        ]
    )
    monkeypatch.setattr(
        ask_ai_module, "chat_completion", lambda *args, **kwargs: next(replies)
    )

    response = ask_ai_module.AskAIService().ask("今日のAI記事を教えて")

    assert response.sources[0].title == "AI systems"
