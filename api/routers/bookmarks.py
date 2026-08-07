from fastapi import APIRouter, Body, Depends, Query

from api.model.models import (
    BookmarkCreate,
    BookmarkFavoriteUpdate,
    BookmarkListResponse,
    BookmarkResponse,
    BookmarkUpdate,
    ErrorResponse,
)
from api.dependencies import get_bookmark_service
from api.services.bookmark_service import BookmarkService

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


@router.post(
    "",
    status_code=201,
    response_model=BookmarkResponse,
    responses={
        409: {"model": ErrorResponse, "description": "Bookmark URL already exists"}
    },
)
def create_bookmark(
    body: BookmarkCreate, service: BookmarkService = Depends(get_bookmark_service)
):
    return service.create(body)


@router.get("", status_code=200, response_model=BookmarkListResponse)
def list_bookmarks(
    folder_id: int | None = None,
    tag_id: int | None = None,
    q: str | None = None,
    is_favorite: bool | None = None,
    sort: list[str] | None = Query(default=None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    service: BookmarkService = Depends(get_bookmark_service),
):
    return service.list(
        folder_id=folder_id,
        tag_id=tag_id,
        q=q,
        is_favorite=is_favorite,
        sort=sort,
        page=page,
        per_page=per_page,
    )


@router.patch(
    "/favorite",
    status_code=200,
    response_model=BookmarkResponse,
)
def set_bookmark_favorite(
    body: BookmarkFavoriteUpdate,
    service: BookmarkService = Depends(get_bookmark_service),
):
    return service.set_favorite(body)


@router.patch(
    "/by-url",
    status_code=200,
    response_model=BookmarkResponse,
    responses={
        409: {"model": ErrorResponse, "description": "Bookmark URL already exists"}
    },
)
def update_bookmark_by_url(
    url: str = Query(...),
    body: BookmarkUpdate = Body(...),
    service: BookmarkService = Depends(get_bookmark_service),
):
    return service.update_by_url(url, body)


@router.get("/by-url", status_code=200, response_model=BookmarkResponse)
def get_bookmark_by_url(
    url: str = Query(...),
    service: BookmarkService = Depends(get_bookmark_service),
):
    return service.get_by_url(url)


@router.get("/{bookmark_id}", status_code=200, response_model=BookmarkResponse)
def get_bookmark(
    bookmark_id: int, service: BookmarkService = Depends(get_bookmark_service)
):
    return service.get(bookmark_id)


@router.patch(
    "/{bookmark_id}",
    status_code=200,
    response_model=BookmarkResponse,
    responses={
        409: {"model": ErrorResponse, "description": "Bookmark URL already exists"}
    },
)
def update_bookmark(
    bookmark_id: int,
    body: BookmarkUpdate,
    service: BookmarkService = Depends(get_bookmark_service),
):
    return service.update(bookmark_id, body)


@router.delete("", status_code=204)
def delete_bookmark(
    bookmark_id: int | None = Query(default=None, alias="id"),
    url: str | None = Query(default=None),
    title: str | None = Query(default=None),
    description: str | None = Query(default=None),
    folder_id: int | None = Query(default=None),
    is_favorite: bool | None = Query(default=None),
    service: BookmarkService = Depends(get_bookmark_service),
):
    service.delete_by_criteria(
        bookmark_id=bookmark_id,
        url=url,
        title=title,
        description=description,
        folder_id=folder_id,
        is_favorite=is_favorite,
    )


@router.delete("/by-url", status_code=204)
def delete_bookmark_by_url(
    url: str = Query(...),
    service: BookmarkService = Depends(get_bookmark_service),
):
    service.delete_by_url(url)


@router.delete("/{bookmark_id}", status_code=204)
def delete_bookmark_by_id(
    bookmark_id: int, service: BookmarkService = Depends(get_bookmark_service)
):
    service.delete_by_criteria(bookmark_id=bookmark_id)
