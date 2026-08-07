from fastapi import APIRouter, Depends

from api.model.models import DashboardMetricsResponse
from api.services.dashboard_service import DashboardService

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/dashboard", status_code=200, response_model=DashboardMetricsResponse)
def get_dashboard_metrics(service: DashboardService = Depends(DashboardService)):
    return service.metrics()
