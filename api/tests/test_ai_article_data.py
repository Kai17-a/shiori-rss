import json
import sqlite3
from contextlib import contextmanager

from api.database import initialize_database
from api.services.ai_article_data_service import AIArticleDataService


def test_lists_saved_ai_article_analysis_data(tmp_path, monkeypatch):
    db_path = str(tmp_path / "ai-data.db")
    initialize_database(db_path)
    with sqlite3.connect(db_path) as conn:
        feed_id = conn.execute(
            "INSERT INTO rss_feeds (url, title) VALUES (?, ?)",
            ("https://example.com/feed.xml", "Example Feed"),
        ).lastrowid
        article_id = conn.execute(
            """
            INSERT INTO rss_feed_articles (feed_id, url, title, summary, published)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                feed_id,
                "https://example.com/article",
                "OpenAI update",
                "Original summary",
                "2026-08-10T01:00:00+00:00",
            ),
        ).lastrowid
        conn.execute(
            """
            INSERT INTO article_ai_analyses (
                source_type, article_id, content_hash, model, prompt_version,
                ai_summary, key_points_json, topics_json, keywords_json,
                entities_json, input_tokens, output_tokens, status
            ) VALUES ('rss', ?, 'hash', 'test-model', 'v1', ?, ?, ?, ?, ?, 120, 40, 'completed')
            """,
            (
                article_id,
                "AI-generated summary",
                json.dumps(["First point"]),
                json.dumps(["AI"]),
                json.dumps(["OpenAI"]),
                json.dumps(["OpenAI"]),
            ),
        )

    import api.services.ai_article_data_service as service_module

    @contextmanager
    def patched_get_db(database_url=db_path):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    monkeypatch.setattr(service_module, "get_db", patched_get_db)

    result = AIArticleDataService().list(q="OpenAI", status="completed")

    assert result.total == 1
    item = result.items[0]
    assert item.source_title == "Example Feed"
    assert item.article_title == "OpenAI update"
    assert item.ai_summary == "AI-generated summary"
    assert item.key_points == ["First point"]
    assert item.topics == ["AI"]
    assert item.keywords == ["OpenAI"]
    assert item.entities == ["OpenAI"]
    assert item.input_tokens == 120
    assert item.output_tokens == 40


def test_ai_article_analysis_filters_can_return_empty_page(tmp_path, monkeypatch):
    db_path = str(tmp_path / "empty-ai-data.db")
    initialize_database(db_path)
    import api.services.ai_article_data_service as service_module

    @contextmanager
    def patched_get_db(database_url=db_path):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    monkeypatch.setattr(service_module, "get_db", patched_get_db)

    result = AIArticleDataService().list(source_type="custom", status="failed")

    assert result.items == []
    assert result.total == 0
    assert result.total_pages == 0
