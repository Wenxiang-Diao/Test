from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.models import User
from app.schemas.schemas import DashboardResponse, PredictionResponse
from app.services.alert_service import AlertRuleService
from app.services.resident_services import DashboardService, PredictionService

router = APIRouter(prefix="/api/residents", tags=["dashboard"])


@router.get("/{resident_id}/dashboard", response_model=DashboardResponse)
def get_dashboard(
    resident_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return DashboardService(db).get_dashboard(resident_id)


@router.get("/{resident_id}/prediction", response_model=PredictionResponse)
def get_prediction(
    resident_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    AlertRuleService(db).evaluate_resident(resident_id)
    return PredictionService(db).get_prediction(resident_id)
