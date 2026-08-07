import sqlite3

from fastapi import HTTPException

from api.database import get_db
from api.model.models import FolderCreate, FolderResponse, FolderUpdate
from api.repositories.folder_repo import FolderRepository
from api.services.base import NamedResourceService


class FolderService(NamedResourceService):
    def _ensure_name_available(
        self,
        repo: FolderRepository,
        name: str,
        folder_id: int | None = None,
    ) -> None:
        super()._ensure_name_available(
            repo,
            name,
            resource_label="Folder",
            already_exists_message="Folder name already exists",
            resource_id=folder_id,
        )

    def create(self, data: FolderCreate) -> FolderResponse:
        with get_db() as conn:
            repo = FolderRepository(conn)
            self._ensure_name_available(repo, data.name)
            try:
                row = repo.insert(data.name, data.description)
            except sqlite3.IntegrityError:
                raise HTTPException(
                    status_code=409, detail="Folder name already exists"
                )
            return FolderResponse(**row)

    def list(self) -> list[FolderResponse]:
        with get_db() as conn:
            repo = FolderRepository(conn)
            rows = repo.find_all()
            return [FolderResponse(**row) for row in rows]

    def get(self, folder_id: int) -> FolderResponse:
        with get_db() as conn:
            repo = FolderRepository(conn)
            row = repo.find_by_id(folder_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Folder not found")
            return FolderResponse(**row)

    def update(self, folder_id: int, data: FolderUpdate) -> FolderResponse:
        with get_db() as conn:
            repo = FolderRepository(conn)
            current = repo.find_by_id(folder_id)
            if current is None:
                raise HTTPException(status_code=404, detail="Folder not found")

            payload = data.model_dump(exclude_unset=True)
            name = payload.get("name", current["name"])
            if name is None:
                raise HTTPException(
                    status_code=422, detail="Folder name cannot be null"
                )
            description = payload.get("description", current["description"])

            self._ensure_name_available(repo, str(name), folder_id=folder_id)
            try:
                row = repo.update(folder_id, str(name), description)
            except sqlite3.IntegrityError:
                raise HTTPException(
                    status_code=409, detail="Folder name already exists"
                )
            if not row:
                raise HTTPException(status_code=404, detail="Folder not found")
            return FolderResponse(**row)

    def delete(self, folder_id: int) -> None:
        with get_db() as conn:
            repo = FolderRepository(conn)
            found = repo.delete(folder_id)
            if not found:
                raise HTTPException(status_code=404, detail="Folder not found")
