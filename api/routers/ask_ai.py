from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from api.dependencies import get_ai_article_data_service, get_ask_ai_service
from api.model.models import AIArticleAnalysisListResponse, AskAIRequest, AskAIResponse
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
