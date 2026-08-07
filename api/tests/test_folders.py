"""Unit tests for Folder API endpoints (Requirements 5.1, 5.2, 5.3, 5.5, 5.6)."""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.tests.test_support import build_test_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient with an isolated in-memory DB for each test."""
    db_path = str(tmp_path / "test.db")
    build_test_db(db_path)

    # Patch get_db to use the temp DB
    import sqlite3
    from contextlib import contextmanager

    import api.database as db_module
    import api.services.folder_service as fs_module

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
    monkeypatch.setattr(fs_module, "get_db", patched_get_db)

    with TestClient(app) as c:
        yield c


# --- Happy path ---


def test_create_folder_returns_201(client):
    response = client.post("/folders", json={"name": "Work", "description": "Notes"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Work"
    assert data["description"] == "Notes"
    assert "id" in data
    assert "created_at" in data


def test_list_folders_returns_200(client):
    client.post("/folders", json={"name": "A", "description": "First"})
    client.post("/folders", json={"name": "B", "description": "Second"})
    response = client.get("/folders")
    assert response.status_code == 200
    items = response.json()
    assert any(item["name"] == "A" and item["description"] == "First" for item in items)
    assert any(
        item["name"] == "B" and item["description"] == "Second" for item in items
    )


def test_delete_folder_returns_204(client):
    create_resp = client.post("/folders", json={"name": "ToDelete"})
    folder_id = create_resp.json()["id"]
    response = client.delete(f"/folders/{folder_id}")
    assert response.status_code == 204


def test_deleted_folder_not_in_list(client):
    create_resp = client.post("/folders", json={"name": "Gone"})
    folder_id = create_resp.json()["id"]
    client.delete(f"/folders/{folder_id}")
    names = [f["name"] for f in client.get("/folders").json()]
    assert "Gone" not in names


# --- Error cases ---


def test_create_folder_without_name_returns_422(client):
    response = client.post("/folders", json={})
    assert response.status_code == 422


def test_create_folder_with_empty_name_returns_422(client):
    response = client.post("/folders", json={"name": "   "})
    assert response.status_code == 422


def test_create_duplicate_folder_returns_409(client):
    client.post("/folders", json={"name": "Work"})
    response = client.post("/folders", json={"name": "Work"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Folder name already exists"


def test_update_folder_to_duplicate_name_returns_409(client):
    first = client.post("/folders", json={"name": "A"}).json()["id"]
    client.post("/folders", json={"name": "B"})
    response = client.patch(f"/folders/{first}", json={"name": "B"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Folder name already exists"


def test_update_folder_can_change_description(client):
    folder_id = client.post(
        "/folders", json={"name": "A", "description": "Old"}
    ).json()["id"]
    response = client.patch(
        f"/folders/{folder_id}",
        json={"description": "New"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "New"


def test_update_folder_can_change_name_without_description(client):
    folder_id = client.post(
        "/folders", json={"name": "A", "description": "Old"}
    ).json()["id"]
    response = client.patch(
        f"/folders/{folder_id}",
        json={"name": "Renamed"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Renamed"
    assert data["description"] == "Old"


def test_delete_nonexistent_folder_returns_404(client):
    response = client.delete("/folders/99999")
    assert response.status_code == 404


def test_create_folder_can_exceed_previous_limit(client):
    for i in range(20):
        response = client.post("/folders", json={"name": f"Folder {i}"})
        assert response.status_code == 201

    response = client.post("/folders", json={"name": "Folder 20"})
    assert response.status_code == 201
    assert response.json()["name"] == "Folder 20"
