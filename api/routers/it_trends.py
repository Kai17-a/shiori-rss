from fastapi import APIRouter, Depends

from api.dependencies import get_it_trend_service
from api.model.models import ITTrendResponse
from api.services.it_trend_service import ITTrendService

router = APIRouter(prefix="/it-trends", tags=["it-trends"])


@router.get("", response_model=ITTrendResponse)
def get_it_trends(service: ITTrendService = Depends(get_it_trend_service)):
    return service.get()


@router.post("/research", response_model=ITTrendResponse)
def research_it_trends(service: ITTrendService = Depends(get_it_trend_service)):
    return service.research()
