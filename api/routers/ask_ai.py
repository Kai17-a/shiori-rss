from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from api.dependencies import (
    get_ai_article_data_service,
    get_article_analysis_service,
    get_ask_ai_service,
)
from api.model.models import (
    AIArticleAnalysisDeleteFailedResponse,
    AIArticleAnalysisListResponse,
    AskAIRequest,
    AskAIResponse,
)
from api.services.article_analysis_service import ArticleAnalysisService
from api.services.ai_article_data_service import AIArticleDataService
from api.services.ask_ai_service import AskAIService

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/article-analyses", response_model=AIArticleAnalysisListResponse)
def list_article_analyses(
    q: str | None = None,
    source_type: Literal["rss", "custom"] | None = None,
    status: Literal["completed", "failed"] | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    service: AIArticleDataService = Depends(get_ai_article_data_service),
):
    return service.list(
        q=q,
        source_type=source_type,
        status=status,
        page=page,
        per_page=per_page,
    )


@router.delete(
    "/article-analyses/failed",
    response_model=AIArticleAnalysisDeleteFailedResponse,
)
def delete_failed_article_analyses(
    service: AIArticleDataService = Depends(get_ai_article_data_service),
    analysis_service: ArticleAnalysisService = Depends(get_article_analysis_service),
):
    if analysis_service.status().running:
        raise HTTPException(
            status_code=409,
            detail="Article analysis is running. Stop it before deleting failed results.",
        )
    return service.delete_failed()


@router.post("/chat", status_code=200, response_model=AskAIResponse)
def ask_ai(body: AskAIRequest, service: AskAIService = Depends(get_ask_ai_service)):
    return service.ask(body.message, body.history, body.context_sources)


@router.post("/chat/stream", status_code=200)
def stream_ask_ai(
    body: AskAIRequest, service: AskAIService = Depends(get_ask_ai_service)
):
    return StreamingResponse(
        service.stream(body.message, body.history, body.context_sources),
        media_type="application/x-ndjson",
    )
