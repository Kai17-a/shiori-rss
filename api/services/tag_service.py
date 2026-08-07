from fastapi import HTTPException

from api.database import get_db
from api.model.models import TagCreate, TagResponse, TagUpdate
from api.repositories.tag_repo import TagRepository
from api.services.base import NamedResourceService


class TagService(NamedResourceService):
    def _ensure_name_available(
        self,
        repo: TagRepository,
        name: str,
        tag_id: int | None = None,
    ) -> None:
        super()._ensure_name_available(
            repo,
            name,
            resource_label="Tag",
            already_exists_message="Tag name already exists",
            resource_id=tag_id,
        )

    def create(self, data: TagCreate) -> TagResponse:
        with get_db() as conn:
            repo = TagRepository(conn)
            self._ensure_name_available(repo, data.name)
            row = repo.insert(data.name, data.description)
            return TagResponse(**row)

    def list(self) -> list[TagResponse]:
        with get_db() as conn:
            repo = TagRepository(conn)
            rows = repo.find_all()
            return [TagResponse(**row) for row in rows]

    def get(self, tag_id: int) -> TagResponse:
        with get_db() as conn:
            repo = TagRepository(conn)
            row = repo.find_by_id(tag_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Tag not found")
            return TagResponse(**row)

    def update(self, tag_id: int, data: TagUpdate) -> TagResponse:
        with get_db() as conn:
            repo = TagRepository(conn)
            current = repo.find_by_id(tag_id)
            if current is None:
                raise HTTPException(status_code=404, detail="Tag not found")

            payload = data.model_dump(exclude_unset=True)
            name = payload.get("name", current["name"])
            if name is None:
                raise HTTPException(status_code=422, detail="Tag name cannot be null")
            description = payload.get("description", current["description"])

            self._ensure_name_available(repo, str(name), tag_id=tag_id)
            row = repo.update(tag_id, str(name), description)
            if not row:
                raise HTTPException(status_code=404, detail="Tag not found")
            return TagResponse(**row)

    def delete(self, tag_id: int) -> None:
        with get_db() as conn:
            repo = TagRepository(conn)
            found = repo.delete(tag_id)
            if not found:
                raise HTTPException(status_code=404, detail="Tag not found")
