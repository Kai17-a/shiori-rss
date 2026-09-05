import sqlite3
import tempfile
from contextlib import contextmanager

from api.database import (
    PLACEHOLDER_VECTOR_EMBEDDING_DIM,
    initialize_database,
    load_vec_extension,
    pack_embedding,
)
from api.tests.test_support import build_test_db


def test_initialize_database_leaves_the_vec0_table_insert_and_query_able():
    """Guards that sqlite-vec stays loadable/usable after a fresh init: if
    this ever regresses (bad install, incompatible SQLite build, etc.),
    semantic search would silently stop working without this failing loudly.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        initialize_database(db_path)

        vector = [0.1] * PLACEHOLDER_VECTOR_EMBEDDING_DIM
        conn = sqlite3.connect(db_path)
        load_vec_extension(conn)
        conn.execute(
            "INSERT INTO article_ai_embeddings(analysis_id, embedding) VALUES (1, ?)",
            (pack_embedding(vector),),
        )
        row = conn.execute(
            "SELECT analysis_id, distance FROM article_ai_embeddings "
            "WHERE embedding MATCH ? ORDER BY distance LIMIT 1",
            (pack_embedding(vector),),
        ).fetchone()
        conn.close()

        assert row == (1, 0.0)
    finally:
        import os

        os.unlink(db_path)


def test_build_test_db_creates_all_tables():
    """The test DB bootstrap must create all required tables."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        build_test_db(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "bookmarks" not in tables
        assert "folders" not in tables
        assert "tags" not in tables
        assert "bookmark_tags" not in tables
        assert "rss_feeds" in tables
        assert "rss_feed_articles" in tables
        assert "app_settings" in tables
        assert "webhook_endpoints" in tables
        assert "rss_feed_webhooks" in tables
        assert "news_sites" in tables
        assert "news_site_articles" in tables
        assert "news_site_webhooks" in tables
        assert "article_search" in tables
        assert "article_ai_analyses" in tables
        assert "article_ai_search" in tables
        assert "article_ai_analysis_usage" in tables
        assert "it_trend_snapshots" in tables
        assert "schema_migrations" in tables
    finally:
        import os

        os.unlink(db_path)


def test_initialize_database_applies_every_migration_idempotently(tmp_path):
    db_path = str(tmp_path / "fresh.db")

    initialize_database(db_path)
    initialize_database(db_path)

    with sqlite3.connect(db_path) as conn:
        versions = {
            row[0]
            for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }
        article_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(rss_feed_articles)").fetchall()
        }
        feed_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(rss_feeds)").fetchall()
        }
        webhook_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(webhook_endpoints)").fetchall()
        }

    assert versions == {
        "010",
        "011",
        "012",
        "013",
        "202604251114",
        "202604251124",
        "202608021000",
        "202608021100",
        "202608021200",
        "202608021300",
        "202608041600",
        "202608081200",
        "202608081300",
        "202608081400",
        "202608090945",
        "202608091010",
        "202608101000",
        "202608121631",
        "202608121710",
        "202608121720",
        "202608121952",
        "202608230029",
        "202608230115",
        "202608271200",
        "202609031300",
        "202609051900",
    }
    assert "published" in article_columns
    assert "summary" in article_columns
    assert "webhook_notified" in article_columns
    assert "notify_webhook_enabled" in feed_columns
    assert {"icon_url", "icon_data", "icon_media_type"} <= feed_columns
    assert "enabled" in webhook_columns


def test_db_error_returns_500(tmp_path, monkeypatch):
    """Database errors from RSS operations are mapped to HTTP 500."""
    from fastapi.testclient import TestClient

    # Mock a DB operation that raises sqlite3.Error
    import api.repositories.rss_feed_repo as repo_module
    import api.database as db_module
    import api.services.rss_feed_service as service_module
    from api.main import app

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

    def mock_insert(*args, **kwargs):
        raise sqlite3.Error("Simulated DB error")

    monkeypatch.setattr(repo_module.RSSFeedRepository, "insert", mock_insert)
    monkeypatch.setattr(db_module, "get_db", patched_get_db)
    monkeypatch.setattr(service_module, "get_db", patched_get_db)
    monkeypatch.setattr(
        service_module.RSSFeedService, "_validate_rss_feed_url", lambda *_: None
    )

    client = TestClient(app)
    response = client.post(
        "/rss-feeds",
        json={"url": "https://example.com/feed.xml", "title": "Test"},
    )

    assert response.status_code == 500
    assert "Database error" in response.json()["detail"]
