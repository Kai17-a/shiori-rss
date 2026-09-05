from typing import Literal

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_article_service
from api.model.models import ArticleListResponse
from api.services.article_service import ArticleService

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", status_code=200, response_model=ArticleListResponse)
def list_articles(
    q: str | None = None,
    source_type: Literal["rss", "custom"] | None = None,
    source_id: int | None = Query(None, ge=1),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    service: ArticleService = Depends(get_article_service),
):
    return service.list_articles(
        q=q,
        source_type=source_type,
        source_id=source_id,
        page=page,
        per_page=per_page,
    )
