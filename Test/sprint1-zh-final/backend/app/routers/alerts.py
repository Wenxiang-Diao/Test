from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.models import User
from app.repositories.repositories import AlertRepository, ResidentRepository
from app.schemas.schemas import AlertItem, AlertListResponse

router = APIRouter(prefix="/api", tags=["alerts"])


def _to_alert_item(alert, resident_name: str) -> AlertItem:
    return AlertItem(
        id=alert.id,
        resident_id=alert.resident_id,
        resident_name=resident_name,
        alert_type=alert.alert_type,
        severity=alert.severity,
        reason=alert.reason,
        timestamp=alert.timestamp,
        suggested_action=alert.suggested_action,
        acknowledged=alert.acknowledged,
    )


@router.get("/alerts", response_model=AlertListResponse)
def list_all_alerts(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = AlertRepository(db)
    resident_repo = ResidentRepository(db)
    name_map = {r.id: r.name for r in resident_repo.list_all()}
    alerts = repo.list_all()
    items = [_to_alert_item(a, name_map.get(a.resident_id, a.resident_id)) for a in alerts]
    return AlertListResponse(alerts=items, total=len(items))


@router.get("/residents/{resident_id}/alerts", response_model=AlertListResponse)
def list_resident_alerts(
    resident_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = AlertRepository(db)
    resident_repo = ResidentRepository(db)
    resident = resident_repo.get_by_id(resident_id)
    name = resident.name if resident else resident_id
    alerts = repo.list_for_resident(resident_id)
    items = [_to_alert_item(a, name) for a in alerts]
    return AlertListResponse(alerts=items, total=len(items))


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from fastapi import HTTPException

    alert = AlertRepository(db).acknowledge(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    return {"message": "告警已确认", "alert_id": alert_id}
