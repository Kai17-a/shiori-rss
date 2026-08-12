from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response

from api.routers.rss_feeds import _validate_public_icon_url

from api.dependencies import get_news_site_service
from api.model.models import (
    ErrorResponse,
    NewsSiteArticleListResponse,
    NewsSiteCreate,
    NewsSiteExecuteResponse,
    NewsSiteListResponse,
    NewsSiteResponse,
    NewsSiteUpdate,
)
from api.services.news_site_service import NewsSiteService

router = APIRouter(prefix="/news-sites", tags=["news-sites"])


@router.post(
    "",
    status_code=201,
    response_model=NewsSiteResponse,
    responses={
        400: {"model": ErrorResponse, "description": "LLM settings are missing"},
        409: {"model": ErrorResponse, "description": "News site URL already exists"},
        422: {"model": ErrorResponse, "description": "The site could not be scraped"},
    },
)
def create_news_site(
    body: NewsSiteCreate,
    service: NewsSiteService = Depends(get_news_site_service),
):
    return service.create(body)


@router.get("", status_code=200, response_model=NewsSiteListResponse)
def list_news_sites(
    q: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    service: NewsSiteService = Depends(get_news_site_service),
):
    return service.list(q=q, page=page, per_page=per_page)


@router.get("/{site_id}", status_code=200, response_model=NewsSiteResponse)
def get_news_site(
    site_id: int, service: NewsSiteService = Depends(get_news_site_service)
):
    return service.get(site_id)


@router.put("/{site_id}/icon", response_model=NewsSiteResponse)
async def upload_news_site_icon(
    site_id: int,
    file: UploadFile = File(...),
    public_url: str = Form(...),
    service: NewsSiteService = Depends(get_news_site_service),
):
    return service.set_icon(
        site_id,
        content=await file.read(),
        media_type=file.content_type or "",
        public_url=_validate_public_icon_url(public_url),
    )


@router.get("/{site_id}/icon")
def get_news_site_icon(
    site_id: int, service: NewsSiteService = Depends(get_news_site_service)
):
    content, media_type = service.get_icon(site_id)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Cache-Control": "no-cache"},
    )


@router.delete("/{site_id}/icon", response_model=NewsSiteResponse)
def delete_news_site_icon(
    site_id: int, service: NewsSiteService = Depends(get_news_site_service)
):
    return service.clear_icon(site_id)


@router.get(
    "/{site_id}/articles", status_code=200, response_model=NewsSiteArticleListResponse
)
def list_news_site_articles(
    site_id: int,
    q: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    published_from: str | None = None,
    published_to: str | None = None,
    service: NewsSiteService = Depends(get_news_site_service),
):
    return service.list_articles(
        site_id,
        q=q,
        page=page,
        per_page=per_page,
        published_from=published_from,
        published_to=published_to,
    )


@router.patch(
    "/{site_id}",
    status_code=200,
    response_model=NewsSiteResponse,
    responses={
        409: {"model": ErrorResponse, "description": "News site URL already exists"}
    },
)
def update_news_site(
    site_id: int,
    body: NewsSiteUpdate,
    service: NewsSiteService = Depends(get_news_site_service),
):
    return service.update(site_id, body)


@router.delete("/{site_id}", status_code=204)
def delete_news_site(
    site_id: int, service: NewsSiteService = Depends(get_news_site_service)
):
    service.delete(site_id)


@router.post(
    "/{site_id}/execute", status_code=200, response_model=NewsSiteExecuteResponse
)
def execute_news_site(
    site_id: int, service: NewsSiteService = Depends(get_news_site_service)
):
    return service.execute(site_id)
