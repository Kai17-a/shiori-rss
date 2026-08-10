from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response

from api.dependencies import get_rss_feed_service
from api.model.models import (
    ErrorResponse,
    RSSFeedCreate,
    RSSFeedArticleListResponse,
    RSSFeedExecuteResponse,
    RSSFeedListResponse,
    RSSFeedResponse,
    RSSFeedUpdate,
)
from api.services.rss_feed_service import RSSFeedService

router = APIRouter(prefix="/rss-feeds", tags=["rss-feeds"])


def _validate_public_icon_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=422, detail="public_url must be an HTTP URL")
    return value


@router.post("", status_code=201, response_model=RSSFeedResponse)
def create_rss_feed(
    body: RSSFeedCreate, service: RSSFeedService = Depends(get_rss_feed_service)
):
    return service.create(body)


@router.get("", status_code=200, response_model=RSSFeedListResponse)
def list_rss_feeds(
    q: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    service: RSSFeedService = Depends(get_rss_feed_service),
):
    return service.list(q=q, page=page, per_page=per_page)


@router.get("/{feed_id}", status_code=200, response_model=RSSFeedResponse)
def get_rss_feed(feed_id: int, service: RSSFeedService = Depends(get_rss_feed_service)):
    return service.get(feed_id)


@router.put("/{feed_id}/icon", response_model=RSSFeedResponse)
async def upload_rss_feed_icon(
    feed_id: int,
    file: UploadFile = File(...),
    public_url: str = Form(...),
    service: RSSFeedService = Depends(get_rss_feed_service),
):
    return service.set_icon(
        feed_id,
        content=await file.read(),
        media_type=file.content_type or "",
        public_url=_validate_public_icon_url(public_url),
    )


@router.get("/{feed_id}/icon")
def get_rss_feed_icon(
    feed_id: int, service: RSSFeedService = Depends(get_rss_feed_service)
):
    content, media_type = service.get_icon(feed_id)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Cache-Control": "no-cache"},
    )


@router.delete("/{feed_id}/icon", response_model=RSSFeedResponse)
def delete_rss_feed_icon(
    feed_id: int, service: RSSFeedService = Depends(get_rss_feed_service)
):
    return service.clear_icon(feed_id)


@router.get(
    "/{feed_id}/articles", status_code=200, response_model=RSSFeedArticleListResponse
)
def list_rss_feed_articles(
    feed_id: int,
    q: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    published_from: str | None = Query(default=None),
    published_to: str | None = Query(default=None),
    service: RSSFeedService = Depends(get_rss_feed_service),
):
    return service.list_articles(
        feed_id,
        q=q,
        page=page,
        per_page=per_page,
        published_from=published_from,
        published_to=published_to,
    )


@router.patch(
    "/{feed_id}",
    status_code=200,
    response_model=RSSFeedResponse,
    responses={
        409: {"model": ErrorResponse, "description": "RSS feed URL already exists"}
    },
)
def update_rss_feed(
    feed_id: int,
    body: RSSFeedUpdate,
    service: RSSFeedService = Depends(get_rss_feed_service),
):
    return service.update(feed_id, body)


@router.delete("/{feed_id}", status_code=204)
def delete_rss_feed(
    feed_id: int, service: RSSFeedService = Depends(get_rss_feed_service)
):
    service.delete(feed_id)


@router.post(
    "/{feed_id}/execute", status_code=200, response_model=RSSFeedExecuteResponse
)
def execute_rss_feed(
    feed_id: int, service: RSSFeedService = Depends(get_rss_feed_service)
):
    return service.execute(feed_id)
