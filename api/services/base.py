from fastapi import HTTPException


class NamedResourceService:
    def _ensure_name_available(
        self,
        repo,
        name: str,
        *,
        resource_label: str,
        already_exists_message: str,
        resource_id: int | None = None,
    ) -> None:
        existing = repo.find_by_name(name)
        if existing is not None and existing["id"] != resource_id:
            raise HTTPException(status_code=409, detail=already_exists_message)

    def _raise_not_found(self, resource_label: str) -> None:
        raise HTTPException(status_code=404, detail=f"{resource_label} not found")
