import sqlite3

from fastapi import HTTPException

from api.database import get_db
from api.model.models import (
    BookmarkCreate,
    BookmarkFavoriteUpdate,
    BookmarkListResponse,
    BookmarkResponse,
    BookmarkUpdate,
)
from api.repositories.bookmark_repo import BookmarkRepository
from api.repositories.folder_repo import FolderRepository
from api.repositories.tag_repo import TagRepository
from api.services.bookmark_base import BookmarkServiceBase


class BookmarkService(BookmarkServiceBase):
    def _build_order_by(self, sort: list[str] | None) -> str:
        allowed_fields = {
            "id": "b.id",
            "url": "b.url",
            "title": "b.title",
            "description": "b.description",
            "folder_id": "b.folder_id",
            "is_favorite": "b.is_favorite",
            "created_at": "b.created_at",
            "updated_at": "b.updated_at",
        }

        if not sort:
            return "ORDER BY b.created_at DESC, b.id DESC"

        clauses: list[str] = []
        for item in sort:
            direction = "ASC"
            field = item
            if item.startswith("-"):
                direction = "DESC"
                field = item[1:]
            elif item.startswith("+"):
                field = item[1:]

            column = allowed_fields.get(field)
            if column is None:
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid sort field: {field}",
                )
            clauses.append(f"{column} {direction}")

        clauses.append("b.id DESC")
        return "ORDER BY " + ", ".join(clauses)

    def _verify_folder(self, conn, folder_id: int) -> None:
        folder_repo = FolderRepository(conn)
        if folder_repo.find_by_id(folder_id) is None:
            raise HTTPException(status_code=404, detail="Folder not found")

    def _verify_tags(self, conn, tag_ids: list[int]) -> None:
        tag_repo = TagRepository(conn)
        missing = [tag_id for tag_id in tag_ids if tag_repo.find_by_id(tag_id) is None]
        if missing:
            raise HTTPException(status_code=404, detail="Tag not found")

    def _sync_tags(
        self, repo: BookmarkRepository, bookmark_id: int, tag_ids: list[int] | None
    ) -> None:
        if tag_ids is None:
            return
        unique_tag_ids = list(dict.fromkeys(tag_ids))
        self._verify_tags(repo.conn, unique_tag_ids)
        repo.set_tags(bookmark_id, unique_tag_ids)

    def create(self, data: BookmarkCreate) -> BookmarkResponse:
        with get_db() as conn:
            if data.folder_id is not None:
                self._verify_folder(conn, data.folder_id)
            repo = BookmarkRepository(conn)
            if repo.find_by_url(str(data.url)) is not None:
                raise HTTPException(
                    status_code=409, detail="Bookmark URL already exists"
                )
            row = repo.insert(
                url=str(data.url),
                title=data.title,
                description=data.description,
                folder_id=data.folder_id,
                is_favorite=False,
            )
            self._sync_tags(repo, row["id"], data.tag_ids)
            saved_row = repo.find_by_id(row["id"])
            assert saved_row is not None
            return self._build_bookmark_response(repo, repo.normalize_row(saved_row))

    def list(
        self,
        folder_id: int | None = None,
        tag_id: int | None = None,
        q: str | None = None,
        is_favorite: bool | None = None,
        sort: list[str] | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> BookmarkListResponse:
        with get_db() as conn:
            repo = BookmarkRepository(conn)
            total = repo.count_all(
                folder_id=folder_id,
                tag_id=tag_id,
                q=q,
                is_favorite=is_favorite,
            )
            total_pages = max((total + per_page - 1) // per_page, 1) if total else 0
            page = max(page, 1)
            if total_pages and page > total_pages:
                page = total_pages
            offset = (page - 1) * per_page
            rows = repo.find_all(
                folder_id=folder_id,
                tag_id=tag_id,
                q=q,
                is_favorite=is_favorite,
                order_by=self._build_order_by(sort),
                limit=per_page,
                offset=offset,
            )
            tags_by_bookmark_id = repo.get_tags_by_bookmark_ids(
                [int(row["id"]) for row in rows]
            )
            items = [
                self._build_bookmark_response(
                    repo,
                    repo.normalize_row(row),
                    tags_by_bookmark_id.get(int(row["id"]), []),
                )
                for row in rows
            ]
            return BookmarkListResponse(
                items=items,
                total=total,
                page=page,
                per_page=per_page,
                total_pages=total_pages,
            )

    def get(self, bookmark_id: int) -> BookmarkResponse:
        with get_db() as conn:
            repo = BookmarkRepository(conn)
            row = repo.find_by_id(bookmark_id)
            if row is None:
                self._raise_not_found("Bookmark")
            assert row is not None
            return self._build_bookmark_response(repo, repo.normalize_row(row))

    def get_by_url(self, url: str) -> BookmarkResponse:
        with get_db() as conn:
            repo = BookmarkRepository(conn)
            row = repo.find_by_url(url)
            if row is None:
                self._raise_not_found("Bookmark")
            assert row is not None
            return self._build_bookmark_response(repo, repo.normalize_row(row))

    def _update_with_repo(
        self, conn, repo: BookmarkRepository, bookmark_id: int, data: BookmarkUpdate
    ) -> BookmarkResponse:
        if repo.find_by_id(bookmark_id) is None:
            self._raise_not_found("Bookmark")

        payload = data.model_dump(exclude_unset=True)
        fields: dict[str, object] = {}
        if "url" in payload:
            url = payload["url"]
            if url is not None:
                fields["url"] = str(url)
        if "title" in payload:
            title = payload["title"]
            if title is not None:
                fields["title"] = title
        if "description" in payload:
            fields["description"] = payload["description"]
        if "folder_id" in payload:
            folder_id = payload["folder_id"]
            if folder_id is not None:
                self._verify_folder(conn, folder_id)
            fields["folder_id"] = folder_id
        if "url" in fields:
            existing = repo.find_by_url(str(fields["url"]))
            if existing is not None and existing["id"] != bookmark_id:
                raise HTTPException(
                    status_code=409, detail="Bookmark URL already exists"
                )

        repo.update(bookmark_id, fields)
        if "tag_ids" in payload:
            self._sync_tags(repo, bookmark_id, payload["tag_ids"])
        row = repo.find_by_id(bookmark_id)
        assert row is not None
        return self._build_bookmark_response(repo, repo.normalize_row(row))

    def update(self, bookmark_id: int, data: BookmarkUpdate) -> BookmarkResponse:
        with get_db() as conn:
            repo = BookmarkRepository(conn)
            return self._update_with_repo(conn, repo, bookmark_id, data)

    def update_by_url(self, url: str, data: BookmarkUpdate) -> BookmarkResponse:
        with get_db() as conn:
            repo = BookmarkRepository(conn)
            row = repo.find_by_url(url)
            if row is None:
                self._raise_not_found("Bookmark")
            assert row is not None
            return self._update_with_repo(conn, repo, int(row["id"]), data)

    def set_favorite(self, data: BookmarkFavoriteUpdate) -> BookmarkResponse:
        with get_db() as conn:
            repo = BookmarkRepository(conn)
            row = repo.find_by_id(data.bookmark_id)
            if row is None:
                self._raise_not_found("Bookmark")

            row = repo.update(data.bookmark_id, {"is_favorite": data.is_favorite})
            assert row is not None
            return self._build_bookmark_response(repo, repo.normalize_row(row))

    def delete(self, bookmark_id: int) -> None:
        with get_db() as conn:
            repo = BookmarkRepository(conn)
            found = repo.delete(bookmark_id)
            if not found:
                raise HTTPException(status_code=404, detail="Bookmark not found")

    def delete_by_url(self, url: str) -> None:
        with get_db() as conn:
            repo = BookmarkRepository(conn)
            row = repo.find_by_url(url)
            if row is None:
                raise HTTPException(status_code=404, detail="Bookmark not found")
            found = repo.delete(int(row["id"]))
            if not found:
                raise HTTPException(status_code=404, detail="Bookmark not found")

    def delete_by_criteria(
        self,
        bookmark_id: int | None = None,
        url: str | None = None,
        title: str | None = None,
        description: str | None = None,
        folder_id: int | None = None,
        is_favorite: bool | None = None,
    ) -> None:
        if (
            bookmark_id is None
            and url is None
            and title is None
            and description is None
            and folder_id is None
            and is_favorite is None
        ):
            raise HTTPException(
                status_code=422,
                detail="At least one bookmark field must be provided",
            )

        with get_db() as conn:
            repo = BookmarkRepository(conn)
            found = repo.delete_by_criteria(
                bookmark_id=bookmark_id,
                url=url,
                title=title,
                description=description,
                folder_id=folder_id,
                is_favorite=is_favorite,
            )
            if not found:
                raise HTTPException(status_code=404, detail="Bookmark not found")

    def add_tag(self, bookmark_id: int, tag_id: int) -> BookmarkResponse:
        with get_db() as conn:
            repo = BookmarkRepository(conn)
            if repo.find_by_id(bookmark_id) is None:
                self._raise_not_found("Bookmark")

            tag_repo = TagRepository(conn)
            if tag_repo.find_by_id(tag_id) is None:
                self._raise_not_found("Tag")

            try:
                repo.add_tag(bookmark_id, tag_id)
            except sqlite3.IntegrityError:
                raise HTTPException(status_code=409, detail="Tag already attached")

            row = repo.find_by_id(bookmark_id)
            assert row is not None
            return self._build_bookmark_response(repo, repo.normalize_row(row))

    def remove_tag(self, bookmark_id: int, tag_id: int) -> None:
        with get_db() as conn:
            repo = BookmarkRepository(conn)
            if repo.find_by_id(bookmark_id) is None:
                self._raise_not_found("Bookmark")

            removed = repo.remove_tag(bookmark_id, tag_id)
            if not removed:
                raise HTTPException(status_code=404, detail="Tag not attached")
