"""Property-based tests for Shiori Keeper API using Hypothesis."""

import sqlite3
from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from api.database import get_db
from api.main import app
from api.tests.test_support import build_test_db

TEST_DB_PATH: str | None = None


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient with an isolated temp DB for each test."""
    global TEST_DB_PATH
    db_path = str(tmp_path / "test.db")
    TEST_DB_PATH = db_path
    build_test_db(db_path)

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


def _create_bookmark(client, url="https://example.com", title="Example", **kwargs):
    payload = {"url": url, "title": title, **kwargs}
    return client.post("/bookmarks", json=payload)


def _create_folder(client, name="folder"):
    return client.post("/folders", json={"name": name})


def _create_tag(client, name="tag"):
    return client.post("/tags", json={"name": name})


def _unique(name: str) -> str:
    return f"{name}-{uuid4().hex[:8]}"


def _reset_database():
    assert TEST_DB_PATH is not None
    with get_db(database_url=TEST_DB_PATH) as conn:
        conn.execute("DELETE FROM bookmark_tags")
        conn.execute("DELETE FROM bookmarks")
        conn.execute("DELETE FROM folders")
        conn.execute("DELETE FROM tags")


# Feature: shiori-keeper-api, Property 1: ブックマーク作成のラウンドトリップ
@given(
    url=st.from_regex(r"https?://[a-z]{3,10}\.[a-z]{2,4}(/[a-z]*)?", fullmatch=True),
    title=st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    ),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_1_bookmark_create_roundtrip(client, url, title):
    """Validates: Requirements 1.1, 2.2"""
    _reset_database()
    resp = _create_bookmark(client, url=_unique(url), title=title)
    assert resp.status_code == 201
    bookmark_id = resp.json()["id"]

    get_resp = client.get(f"/bookmarks/{bookmark_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == title


# Feature: shiori-keeper-api, Property 2: 無効URLのバリデーション拒否
@given(
    url=st.text(min_size=1).filter(lambda s: not s.startswith(("http://", "https://"))),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_2_invalid_url_returns_422(client, url):
    """Validates: Requirements 1.3, 3.4"""
    _reset_database()
    resp = client.post("/bookmarks", json={"url": url, "title": "test"})
    assert resp.status_code == 422


# Feature: shiori-keeper-api, Property 3: 存在しないリソースへのアクセスは404
@given(
    nonexistent_id=st.integers(min_value=10000, max_value=99999),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_3_nonexistent_resource_returns_404(client, nonexistent_id):
    """Validates: Requirements 1.5, 2.6, 3.3, 4.3, 5.6, 6.6, 7.4"""
    _reset_database()
    assert client.get(f"/bookmarks/{nonexistent_id}").status_code == 404
    assert (
        client.patch(f"/bookmarks/{nonexistent_id}", json={"title": "x"}).status_code
        == 404
    )
    assert client.delete(f"/bookmarks/{nonexistent_id}").status_code == 404
    assert client.delete(f"/folders/{nonexistent_id}").status_code == 404
    assert client.delete(f"/tags/{nonexistent_id}").status_code == 404


# Feature: shiori-keeper-api, Property 4: フォルダフィルタの正確性
@given(
    folder_count=st.integers(min_value=1, max_value=3),
    bookmark_count=st.integers(min_value=1, max_value=5),
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_property_4_folder_filter_accuracy(client, folder_count, bookmark_count):
    """Validates: Requirements 2.3"""
    _reset_database()
    # Create folders
    folder_ids = []
    for i in range(folder_count):
        resp = _create_folder(client, name=f"folder{i}")
        assert resp.status_code == 201
        folder_ids.append(resp.json()["id"])

    # Create bookmarks distributed across folders
    for i in range(bookmark_count):
        folder_id = folder_ids[i % folder_count]
        resp = _create_bookmark(
            client,
            url=_unique(f"https://example{i}.com"),
            title=f"Bookmark{i}",
            folder_id=folder_id,
        )
        assert resp.status_code == 201

    # Verify filter accuracy for each folder
    for folder_id in folder_ids:
        resp = client.get(f"/bookmarks?folder_id={folder_id}")
        assert resp.status_code == 200
        bookmarks = resp.json()
        for bm in bookmarks:
            assert bm["folder_id"] == folder_id


# Feature: shiori-keeper-api, Property 5: タグフィルタの正確性
@given(
    tag_count=st.integers(min_value=1, max_value=3),
    bookmark_count=st.integers(min_value=1, max_value=5),
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_property_5_tag_filter_accuracy(client, tag_count, bookmark_count):
    """Validates: Requirements 2.4"""
    _reset_database()
    # Create tags
    tag_ids = []
    for i in range(tag_count):
        resp = _create_tag(client, name=_unique(f"tag{i}"))
        assert resp.status_code == 201
        tag_ids.append(resp.json()["id"])

    # Create bookmarks and assign tags
    bm_ids_by_tag = {tid: [] for tid in tag_ids}
    for i in range(bookmark_count):
        resp = _create_bookmark(
            client, url=_unique(f"https://site{i}.com"), title=f"Site{i}"
        )
        assert resp.status_code == 201
        bm_id = resp.json()["id"]
        tag_id = tag_ids[i % tag_count]
        tag_resp = client.post(f"/bookmarks/{bm_id}/tags", json={"tag_id": tag_id})
        assert tag_resp.status_code == 200
        bm_ids_by_tag[tag_id].append(bm_id)

    # Verify filter accuracy for each tag
    for tag_id in tag_ids:
        resp = client.get(f"/bookmarks?tag_id={tag_id}")
        assert resp.status_code == 200
        bookmarks = resp.json()
        for bm in bookmarks:
            tag_ids_in_bm = [t["id"] for t in bm["tags"]]
            assert tag_id in tag_ids_in_bm


# Feature: shiori-keeper-api, Property 6: キーワード検索の正確性
@given(
    q=st.text(min_size=2, max_size=5, alphabet="abcdefghijklmnopqrstuvwxyz"),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_6_keyword_search_accuracy(client, q):
    """Validates: Requirements 2.5"""
    _reset_database()
    # Create a bookmark whose title contains q
    resp = _create_bookmark(
        client, url=_unique("https://example.com"), title=f"prefix{q}suffix"
    )
    assert resp.status_code == 201

    # Search and verify all results contain q in title or url
    resp = client.get(f"/bookmarks?q={q}")
    assert resp.status_code == 200
    bookmarks = resp.json()
    assert len(bookmarks) >= 1
    for bm in bookmarks:
        assert q in bm["title"] or q in bm["url"]


# Feature: shiori-keeper-api, Property 7: 部分更新の不変性
@given(
    new_title=st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    ),
)
@settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
)
def test_property_7_partial_update_immutability(client, new_title):
    """Validates: Requirements 3.1, 3.2"""
    _reset_database()
    original_url = _unique("https://original.com")
    original_desc = "original description"
    resp = _create_bookmark(
        client, url=original_url, title="OriginalTitle", description=original_desc
    )
    assert resp.status_code == 201
    original = resp.json()
    bm_id = original["id"]

    # Patch only title
    patch_resp = client.patch(f"/bookmarks/{bm_id}", json={"title": new_title})
    assert patch_resp.status_code == 200
    updated = patch_resp.json()

    # Title changed
    assert updated["title"] == new_title
    # Other fields unchanged
    assert updated["url"] == original["url"]
    assert updated["description"] == original["description"]
    assert updated["folder_id"] == original["folder_id"]
    assert updated["id"] == original["id"]


# Feature: shiori-keeper-api, Property 8: ブックマーク削除とカスケード
@given(
    tag_count=st.integers(min_value=1, max_value=3),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_8_bookmark_delete_cascade(client, tag_count):
    """Validates: Requirements 4.1, 4.2"""
    _reset_database()
    # Create bookmark with tags
    resp = _create_bookmark(
        client, url=_unique("https://delete-me.com"), title="ToDelete"
    )
    assert resp.status_code == 201
    bm_id = resp.json()["id"]

    for i in range(tag_count):
        tag_resp = _create_tag(client, name=_unique(f"deltag{i}"))
        assert tag_resp.status_code == 201
        tag_id = tag_resp.json()["id"]
        attach_resp = client.post(f"/bookmarks/{bm_id}/tags", json={"tag_id": tag_id})
        assert attach_resp.status_code == 200

    # Delete bookmark
    del_resp = client.delete(f"/bookmarks/{bm_id}")
    assert del_resp.status_code == 204

    # Verify 404 on GET
    get_resp = client.get(f"/bookmarks/{bm_id}")
    assert get_resp.status_code == 404


# Feature: shiori-keeper-api, Property 9: フォルダ削除後のブックマーク参照解除
@given(
    bookmark_count=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_9_folder_delete_nullifies_bookmark_folder(client, bookmark_count):
    """Validates: Requirements 5.4"""
    _reset_database()
    # Create folder
    folder_resp = _create_folder(client, name="tempfolder")
    assert folder_resp.status_code == 201
    folder_id = folder_resp.json()["id"]

    # Create bookmarks in that folder
    bm_ids = []
    for i in range(bookmark_count):
        resp = _create_bookmark(
            client,
            url=_unique(f"https://infolder{i}.com"),
            title=f"InFolder{i}",
            folder_id=folder_id,
        )
        assert resp.status_code == 201
        bm_ids.append(resp.json()["id"])

    # Delete folder
    del_resp = client.delete(f"/folders/{folder_id}")
    assert del_resp.status_code == 204

    # Verify bookmarks have folder_id = null
    for bm_id in bm_ids:
        get_resp = client.get(f"/bookmarks/{bm_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["folder_id"] is None


# Feature: shiori-keeper-api, Property 10: タグ名の一意性
@given(
    tag_name=st.text(min_size=1, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz"),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_10_tag_name_uniqueness(client, tag_name):
    """Validates: Requirements 6.5"""
    _reset_database()
    first = _create_tag(client, name=tag_name)
    assert first.status_code == 201

    second = _create_tag(client, name=tag_name)
    assert second.status_code == 409


# Feature: shiori-keeper-api, Property 11: タグ付与・解除のラウンドトリップ
@given(
    tag_count=st.integers(min_value=1, max_value=3),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_11_tag_attach_detach_roundtrip(client, tag_count):
    """Validates: Requirements 7.1, 7.2"""
    _reset_database()
    # Create bookmark (starts with no tags)
    resp = _create_bookmark(
        client, url=_unique("https://roundtrip.com"), title="RoundTrip"
    )
    assert resp.status_code == 201
    bm_id = resp.json()["id"]
    assert resp.json()["tags"] == []

    # Create and attach tags
    tag_ids = []
    for i in range(tag_count):
        tag_resp = _create_tag(client, name=_unique(f"rttag{i}"))
        assert tag_resp.status_code == 201
        tag_id = tag_resp.json()["id"]
        tag_ids.append(tag_id)
        attach_resp = client.post(f"/bookmarks/{bm_id}/tags", json={"tag_id": tag_id})
        assert attach_resp.status_code == 200

    # Detach all tags
    for tag_id in tag_ids:
        detach_resp = client.delete(f"/bookmarks/{bm_id}/tags/{tag_id}")
        assert detach_resp.status_code == 204

    # Verify tags list is empty again
    get_resp = client.get(f"/bookmarks/{bm_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["tags"] == []


# Feature: shiori-keeper-api, Property 12: タグの重複付与は409
@given(
    dummy=st.integers(min_value=0, max_value=0),  # force Hypothesis to run 100 examples
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_12_duplicate_tag_attach_returns_409(client, dummy):
    """Validates: Requirements 7.3"""
    _reset_database()
    resp = _create_bookmark(client, url=_unique("https://dup-tag.com"), title="DupTag")
    assert resp.status_code == 201
    bm_id = resp.json()["id"]

    tag_resp = _create_tag(client, name="duptag")
    assert tag_resp.status_code == 201
    tag_id = tag_resp.json()["id"]

    first = client.post(f"/bookmarks/{bm_id}/tags", json={"tag_id": tag_id})
    assert first.status_code == 200

    second = client.post(f"/bookmarks/{bm_id}/tags", json={"tag_id": tag_id})
    assert second.status_code == 409
