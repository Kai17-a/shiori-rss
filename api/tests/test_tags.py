"""Unit tests for Tag API endpoints (Requirements 6.1, 6.2, 6.3, 6.5, 6.6)."""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.tests.test_support import build_test_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient with an isolated temp DB for each test."""
    db_path = str(tmp_path / "test.db")
    build_test_db(db_path)

    import api.database as db_module
    import api.services.tag_service as ts_module
    from contextlib import contextmanager
    import sqlite3

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
    monkeypatch.setattr(ts_module, "get_db", patched_get_db)

    with TestClient(app) as c:
        yield c


# --- Happy path ---


def test_create_tag_returns_201(client):
    response = client.post("/tags", json={"name": "python", "description": "Lang"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "python"
    assert data["description"] == "Lang"
    assert "id" in data


def test_list_tags_returns_200(client):
    client.post("/tags", json={"name": "alpha", "description": "First"})
    client.post("/tags", json={"name": "beta", "description": "Second"})
    response = client.get("/tags")
    assert response.status_code == 200
    items = response.json()
    assert any(
        item["name"] == "alpha" and item["description"] == "First" for item in items
    )
    assert any(
        item["name"] == "beta" and item["description"] == "Second" for item in items
    )


def test_delete_tag_returns_204(client):
    create_resp = client.post("/tags", json={"name": "removeme"})
    tag_id = create_resp.json()["id"]
    response = client.delete(f"/tags/{tag_id}")
    assert response.status_code == 204


def test_deleted_tag_not_in_list(client):
    create_resp = client.post("/tags", json={"name": "gone"})
    tag_id = create_resp.json()["id"]
    client.delete(f"/tags/{tag_id}")
    names = [t["name"] for t in client.get("/tags").json()]
    assert "gone" not in names


# --- Error cases ---


def test_create_duplicate_tag_returns_409(client):
    client.post("/tags", json={"name": "unique"})
    response = client.post("/tags", json={"name": "unique"})
    assert response.status_code == 409


def test_create_tag_with_empty_name_returns_422(client):
    response = client.post("/tags", json={"name": "   "})
    assert response.status_code == 422


def test_update_tag_to_duplicate_name_returns_409(client):
    first = client.post("/tags", json={"name": "alpha"}).json()["id"]
    client.post("/tags", json={"name": "beta"})
    response = client.patch(f"/tags/{first}", json={"name": "beta"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Tag name already exists"


def test_update_tag_can_change_description(client):
    tag_id = client.post("/tags", json={"name": "alpha", "description": "Old"}).json()[
        "id"
    ]
    response = client.patch(
        f"/tags/{tag_id}",
        json={"description": "New"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "New"


def test_update_tag_can_change_name_without_description(client):
    tag_id = client.post("/tags", json={"name": "alpha", "description": "Old"}).json()[
        "id"
    ]
    response = client.patch(
        f"/tags/{tag_id}",
        json={"name": "beta"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "beta"
    assert data["description"] == "Old"


def test_delete_nonexistent_tag_returns_404(client):
    response = client.delete("/tags/99999")
    assert response.status_code == 404


def test_create_tag_can_exceed_previous_limit(client):
    for i in range(20):
        response = client.post("/tags", json={"name": f"tag-{i}"})
        assert response.status_code == 201

    response = client.post("/tags", json={"name": "tag-20"})
    assert response.status_code == 201
    assert response.json()["name"] == "tag-20"
