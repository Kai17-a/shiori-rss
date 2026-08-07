"""Unit tests for Bookmark API endpoints (Requirements 1.1-1.5, 2.1-2.6, 3.1-3.4, 4.1-4.3, 7.1-7.4)."""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.tests.test_support import build_test_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient with an isolated temp DB for each test."""
    db_path = str(tmp_path / "test.db")
    build_test_db(db_path)

    import sqlite3
    from contextlib import contextmanager

    import api.database as db_module
    import api.services.bookmark_service as bs_module
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
    monkeypatch.setattr(fs_module, "get_db", patched_get_db)
    monkeypatch.setattr(ts_module, "get_db", patched_get_db)

    with TestClient(app) as c:
        yield c


# --- Helpers ---


def create_bookmark(client, url="https://example.com", title="Example", **kwargs):
    payload = {"url": url, "title": title, **kwargs}
    return client.post("/bookmarks", json=payload)


def create_folder(client, name="MyFolder"):
    return client.post("/folders", json={"name": name})


def create_tag(client, name="mytag"):
    return client.post("/tags", json={"name": name})


# --- Happy path ---


def test_create_bookmark_returns_201(client):
    resp = create_bookmark(client)
    assert resp.status_code == 201
    data = resp.json()
    assert data["url"] == "https://example.com/"
    assert data["title"] == "Example"
    assert data["is_favorite"] is False
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert data["tags"] == []


def test_create_bookmark_accepts_tag_ids(client):
    tag_a = create_tag(client, name="a").json()["id"]
    tag_b = create_tag(client, name="b").json()["id"]
    resp = create_bookmark(client, tag_ids=[tag_a, tag_b])
    assert resp.status_code == 201
    tag_ids = [t["id"] for t in resp.json()["tags"]]
    assert tag_ids == [tag_a, tag_b]


def test_list_bookmarks_returns_200(client):
    create_bookmark(client, url="https://a.com", title="A")
    create_bookmark(client, url="https://b.com", title="B")
    resp = client.get("/bookmarks")
    assert resp.status_code == 200
    body = resp.json()
    titles = [b["title"] for b in body["items"]]
    assert "A" in titles
    assert "B" in titles
    assert body["page"] == 1
    assert body["per_page"] == 20


def test_list_bookmarks_paginates_by_default(client):
    for i in range(21):
        create_bookmark(client, url=f"https://{i}.example.com", title=f"B{i}")
    resp = client.get("/bookmarks")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 20
    assert body["total"] == 21
    assert body["total_pages"] == 2


def test_list_bookmarks_accepts_page_and_per_page(client):
    for i in range(5):
        create_bookmark(client, url=f"https://{i}.example.com", title=f"B{i}")
    resp = client.get("/bookmarks?page=2&per_page=2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 2
    assert body["per_page"] == 2
    assert len(body["items"]) == 2


def test_list_bookmarks_accepts_multiple_sort_fields(client):
    create_bookmark(client, url="https://example.com/c", title="C")
    create_bookmark(client, url="https://example.com/a", title="A")
    create_bookmark(client, url="https://example.com/b", title="A")

    resp = client.get("/bookmarks?sort=title&sort=url")
    assert resp.status_code == 200
    titles_and_urls = [(b["title"], b["url"]) for b in resp.json()["items"]]
    assert titles_and_urls == [
        ("A", "https://example.com/a"),
        ("A", "https://example.com/b"),
        ("C", "https://example.com/c"),
    ]


def test_list_bookmarks_accepts_desc_sort_prefix(client):
    create_bookmark(client, url="https://example.com/a", title="A")
    create_bookmark(client, url="https://example.com/c", title="C")
    create_bookmark(client, url="https://example.com/b", title="B")

    resp = client.get("/bookmarks?sort=-title")
    assert resp.status_code == 200
    titles = [b["title"] for b in resp.json()["items"]]
    assert titles == ["C", "B", "A"]


def test_list_bookmarks_rejects_unknown_sort_field(client):
    resp = client.get("/bookmarks?sort=unknown")
    assert resp.status_code == 422


def test_list_bookmarks_filters_by_is_favorite(client):
    favorite_id = create_bookmark(
        client, url="https://favorite.example.com", title="Favorite"
    ).json()["id"]
    create_bookmark(client, url="https://regular.example.com", title="Regular")
    client.patch(
        "/bookmarks/favorite",
        json={"bookmark_id": favorite_id, "is_favorite": True},
    )

    resp = client.get("/bookmarks?is_favorite=true")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert [item["title"] for item in body["items"]] == ["Favorite"]


def test_get_bookmark_returns_200(client):
    bm_id = create_bookmark(client).json()["id"]
    resp = client.get(f"/bookmarks/{bm_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == bm_id


def test_update_bookmark_returns_200(client):
    bm_id = create_bookmark(client, title="Old").json()["id"]
    resp = client.patch(f"/bookmarks/{bm_id}", json={"title": "New"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"


def test_update_bookmark_by_url_returns_200(client):
    url = create_bookmark(client, title="Old").json()["url"]
    resp = client.patch(
        "/bookmarks/by-url",
        params={"url": url},
        json={"title": "New"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"


def test_update_bookmark_by_url_returns_404_for_missing_url(client):
    resp = client.patch(
        "/bookmarks/by-url",
        params={"url": "https://missing.example.com"},
        json={"title": "New"},
    )
    assert resp.status_code == 404


def test_update_bookmark_by_url_returns_409_for_duplicate_url(client):
    create_bookmark(client, url="https://first.example.com", title="First")
    second_url = create_bookmark(
        client, url="https://second.example.com", title="Second"
    ).json()["url"]
    resp = client.patch(
        "/bookmarks/by-url",
        params={"url": second_url},
        json={"url": "https://first.example.com"},
    )
    assert resp.status_code == 409


def test_update_bookmark_can_replace_tags(client):
    tag_a = create_tag(client, name="a").json()["id"]
    tag_b = create_tag(client, name="b").json()["id"]
    bm_id = create_bookmark(client, tag_ids=[tag_a]).json()["id"]
    resp = client.patch(f"/bookmarks/{bm_id}", json={"tag_ids": [tag_b]})
    assert resp.status_code == 200
    tag_ids = [t["id"] for t in resp.json()["tags"]]
    assert tag_ids == [tag_b]


def test_update_bookmark_can_clear_tags(client):
    tag_id = create_tag(client).json()["id"]
    bm_id = create_bookmark(client, tag_ids=[tag_id]).json()["id"]
    resp = client.patch(f"/bookmarks/{bm_id}", json={"tag_ids": []})
    assert resp.status_code == 200
    assert resp.json()["tags"] == []


def test_update_bookmark_can_clear_description_and_folder(client):
    folder_id = create_folder(client).json()["id"]
    bm_id = create_bookmark(
        client,
        description="Original description",
        folder_id=folder_id,
    ).json()["id"]

    resp = client.patch(
        f"/bookmarks/{bm_id}",
        json={"description": None, "folder_id": None},
    )

    assert resp.status_code == 200
    assert resp.json()["description"] is None
    assert resp.json()["folder_id"] is None


@pytest.mark.parametrize("payload", [{"url": None}, {"title": None}, {"tag_ids": None}])
def test_update_bookmark_rejects_null_for_non_nullable_fields(client, payload):
    bm_id = create_bookmark(client).json()["id"]

    resp = client.patch(f"/bookmarks/{bm_id}", json=payload)

    assert resp.status_code == 422


def test_update_bookmark_changes_updated_at(client):
    bm = create_bookmark(client).json()
    bm_id = bm["id"]
    old_updated = bm["updated_at"]
    resp = client.patch(f"/bookmarks/{bm_id}", json={"title": "Changed"})
    assert resp.json()["updated_at"] != old_updated


def test_set_bookmark_favorite_returns_200(client):
    bm_id = create_bookmark(client).json()["id"]
    resp = client.patch(
        "/bookmarks/favorite", json={"bookmark_id": bm_id, "is_favorite": True}
    )
    assert resp.status_code == 200
    assert resp.json()["is_favorite"] is True


def test_unset_bookmark_favorite_returns_200(client):
    bm_id = create_bookmark(client).json()["id"]
    client.patch(
        "/bookmarks/favorite", json={"bookmark_id": bm_id, "is_favorite": True}
    )
    resp = client.patch(
        "/bookmarks/favorite", json={"bookmark_id": bm_id, "is_favorite": False}
    )
    assert resp.status_code == 200
    assert resp.json()["is_favorite"] is False


def test_delete_bookmark_returns_204(client):
    bm_id = create_bookmark(client).json()["id"]
    resp = client.delete("/bookmarks", params={"id": bm_id})
    assert resp.status_code == 204


def test_delete_bookmark_by_url_returns_204(client):
    url = create_bookmark(client).json()["url"]
    resp = client.delete("/bookmarks/by-url", params={"url": url})
    assert resp.status_code == 204


def test_delete_bookmark_by_title_returns_204(client):
    title = "Delete Me"
    create_bookmark(client, url="https://delete-by-title.example.com", title=title)
    resp = client.delete("/bookmarks", params={"title": title})
    assert resp.status_code == 204


def test_delete_bookmark_by_url_and_title_returns_204(client):
    title = "Delete Together"
    url = create_bookmark(client, url="https://delete-together.example.com", title=title).json()["url"]
    resp = client.delete("/bookmarks", params={"url": url, "title": title})
    assert resp.status_code == 204


def test_delete_bookmark_by_id_returns_204(client):
    bm_id = create_bookmark(client).json()["id"]
    resp = client.delete("/bookmarks", params={"id": bm_id})
    assert resp.status_code == 204


def test_delete_bookmark_by_folder_id_returns_204(client):
    folder_id = create_folder(client).json()["id"]
    create_bookmark(client, url="https://folder-delete.example.com", folder_id=folder_id)
    resp = client.delete("/bookmarks", params={"folder_id": folder_id})
    assert resp.status_code == 204


def test_delete_bookmark_by_is_favorite_returns_204(client):
    bm_id = create_bookmark(client).json()["id"]
    client.patch(
        "/bookmarks/favorite", json={"bookmark_id": bm_id, "is_favorite": True}
    )
    resp = client.delete("/bookmarks", params={"is_favorite": True})
    assert resp.status_code == 204


def test_delete_bookmark_by_url_and_title_returns_404_when_not_matching_and(client):
    create_bookmark(client, url="https://keep.example.com", title="Keep")
    resp = client.delete(
        "/bookmarks",
        params={"url": "https://keep.example.com", "title": "Wrong"},
    )
    assert resp.status_code == 404


def test_delete_bookmark_without_criteria_returns_422(client):
    resp = client.delete("/bookmarks")
    assert resp.status_code == 422


def test_deleted_bookmark_returns_404(client):
    bm_id = create_bookmark(client).json()["id"]
    client.delete("/bookmarks", params={"id": bm_id})
    resp = client.get(f"/bookmarks/{bm_id}")
    assert resp.status_code == 404


def test_create_bookmark_with_folder(client):
    folder_id = create_folder(client).json()["id"]
    resp = create_bookmark(client, folder_id=folder_id)
    assert resp.status_code == 201
    assert resp.json()["folder_id"] == folder_id


# --- Error cases ---


def test_create_bookmark_without_title_returns_422(client):
    resp = client.post("/bookmarks", json={"url": "https://example.com"})
    assert resp.status_code == 422


def test_create_bookmark_with_invalid_url_returns_422(client):
    resp = client.post("/bookmarks", json={"url": "not-a-url", "title": "Test"})
    assert resp.status_code == 422


def test_create_bookmark_with_ftp_url_returns_422(client):
    resp = client.post("/bookmarks", json={"url": "ftp://example.com", "title": "Test"})
    assert resp.status_code == 422


def test_get_nonexistent_bookmark_returns_404(client):
    resp = client.get("/bookmarks/99999")
    assert resp.status_code == 404


def test_update_nonexistent_bookmark_returns_404(client):
    resp = client.patch("/bookmarks/99999", json={"title": "X"})
    assert resp.status_code == 404


def test_delete_nonexistent_bookmark_by_url_returns_404(client):
    resp = client.delete("/bookmarks", params={"url": "https://example.com/missing"})
    assert resp.status_code == 404


def test_create_bookmark_with_nonexistent_folder_returns_404(client):
    resp = create_bookmark(client, folder_id=99999)
    assert resp.status_code == 404


def test_update_bookmark_with_invalid_url_returns_422(client):
    bm_id = create_bookmark(client).json()["id"]
    resp = client.patch(f"/bookmarks/{bm_id}", json={"url": "bad-url"})
    assert resp.status_code == 422


def test_create_bookmark_with_empty_title_returns_422(client):
    resp = client.post(
        "/bookmarks", json={"url": "https://example.com", "title": "   "}
    )
    assert resp.status_code == 422


def test_create_bookmark_with_duplicate_tag_ids_returns_422(client):
    tag_id = create_tag(client).json()["id"]
    resp = create_bookmark(client, tag_ids=[tag_id, tag_id])
    assert resp.status_code == 422


def test_create_bookmark_with_missing_tag_returns_404(client):
    resp = create_bookmark(client, tag_ids=[99999])
    assert resp.status_code == 404


def test_update_bookmark_with_duplicate_tag_ids_returns_422(client):
    tag_id = create_tag(client).json()["id"]
    bm_id = create_bookmark(client).json()["id"]
    resp = client.patch(f"/bookmarks/{bm_id}", json={"tag_ids": [tag_id, tag_id]})
    assert resp.status_code == 422


def test_create_bookmark_with_duplicate_url_returns_409(client):
    create_bookmark(client, url="https://dup.example", title="First")
    resp = create_bookmark(client, url="https://dup.example", title="Second")
    assert resp.status_code == 409


def test_update_bookmark_with_duplicate_url_returns_409(client):
    first_id = create_bookmark(
        client, url="https://first.example", title="First"
    ).json()["id"]
    create_bookmark(client, url="https://second.example", title="Second")
    resp = client.patch(
        f"/bookmarks/{first_id}",
        json={"url": "https://second.example"},
    )
    assert resp.status_code == 409
