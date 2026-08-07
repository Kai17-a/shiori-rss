"""Unit tests for dashboard metrics API endpoints."""

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
    import api.services.bookmark_service as bs_module
    import api.services.dashboard_service as ds_module
    import api.services.folder_service as fs_module
    import api.services.tag_service as ts_module

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
    monkeypatch.setattr(bs_module, "get_db", patched_get_db)
    monkeypatch.setattr(ds_module, "get_db", patched_get_db)
    monkeypatch.setattr(fs_module, "get_db", patched_get_db)
    monkeypatch.setattr(ts_module, "get_db", patched_get_db)

    with TestClient(app) as c:
        yield c


def test_dashboard_metrics_returns_zero_counts(client):
    resp = client.get("/metrics/dashboard")
    assert resp.status_code == 200
    assert resp.json() == {
        "bookmarks_total": 0,
        "folders_total": 0,
        "tags_total": 0,
        "favorites_total": 0,
        "rss_feeds_total": 0,
        "news_sites_total": 0,
    }


def test_dashboard_metrics_counts_resources(client):
    folder_resp = client.post("/folders", json={"name": "Work"})
    assert folder_resp.status_code == 201

    tag_resp = client.post("/tags", json={"name": "python"})
    assert tag_resp.status_code == 201

    bookmark_a = client.post(
        "/bookmarks",
        json={"url": "https://example.com", "title": "Example"},
    )
    assert bookmark_a.status_code == 201

    bookmark_b = client.post(
        "/bookmarks",
        json={"url": "https://example.org", "title": "Example Org"},
    )
    assert bookmark_b.status_code == 201

    favorite_resp = client.patch(
        "/bookmarks/favorite",
        json={"bookmark_id": bookmark_a.json()["id"], "is_favorite": True},
    )
    assert favorite_resp.status_code == 200

    resp = client.get("/metrics/dashboard")
    assert resp.status_code == 200
    assert resp.json() == {
        "bookmarks_total": 2,
        "folders_total": 1,
        "tags_total": 1,
        "favorites_total": 1,
        "rss_feeds_total": 0,
        "news_sites_total": 0,
    }
