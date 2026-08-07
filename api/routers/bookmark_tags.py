from api.model.models import BookmarkResponse, TagAttach
from fastapi import APIRouter, Depends

from api.dependencies import get_bookmark_service
from api.services.bookmark_service import BookmarkService

router = APIRouter(prefix="/bookmarks", tags=["bookmark-tags"])


@router.post("/{bookmark_id}/tags", status_code=200, response_model=BookmarkResponse)
def add_tag(
    bookmark_id: int,
    body: TagAttach,
    service: BookmarkService = Depends(get_bookmark_service),
):
    return service.add_tag(bookmark_id, body.tag_id)


@router.delete("/{bookmark_id}/tags/{tag_id}", status_code=204)
def remove_tag(
    bookmark_id: int,
    tag_id: int,
    service: BookmarkService = Depends(get_bookmark_service),
):
    service.remove_tag(bookmark_id, tag_id)
