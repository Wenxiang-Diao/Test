from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.models import User
from app.schemas.schemas import ReportResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{resident_id}", response_model=ReportResponse)
def get_report(
    resident_id: str,
    target_date: date | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ReportService(db).get_report(resident_id, target_date)
