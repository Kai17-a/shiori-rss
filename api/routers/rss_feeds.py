from fastapi import APIRouter, Depends, Query

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


@router.get("/{feed_id}/articles", status_code=200, response_model=RSSFeedArticleListResponse)
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
