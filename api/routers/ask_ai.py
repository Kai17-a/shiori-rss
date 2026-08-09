from fastapi import APIRouter, Depends

from api.dependencies import get_ask_ai_service
from api.model.models import AskAIRequest, AskAIResponse
from api.services.ask_ai_service import AskAIService

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", status_code=200, response_model=AskAIResponse)
def ask_ai(body: AskAIRequest, service: AskAIService = Depends(get_ask_ai_service)):
    return service.ask(body.message)
