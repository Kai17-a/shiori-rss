from fastapi import APIRouter, Depends, Query

from api.dependencies import get_dashboard_service
from api.model.models import DashboardResponse
from api.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", status_code=200, response_model=DashboardResponse)
def get_dashboard(
    limit: int = Query(100, ge=1, le=100),
    service: DashboardService = Depends(get_dashboard_service),
):
    return service.get(limit)
