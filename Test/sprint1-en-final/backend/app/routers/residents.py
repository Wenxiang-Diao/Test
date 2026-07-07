from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.models import User
from app.schemas.schemas import (
    ResidentCard,
    ResidentCreate,
    ResidentDetail,
    ResidentTransferRequest,
    ResidentUpdate,
)
from app.services.resident_services import ResidentService

router = APIRouter(prefix="/api/residents", tags=["residents"])


@router.get("", response_model=list[ResidentCard])
def list_residents(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ResidentService(db).list_residents()


@router.get("/manage", response_model=list[ResidentDetail])
def list_residents_for_management(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ResidentService(db).list_details()


@router.post("", response_model=ResidentDetail)
def create_resident(
    body: ResidentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ResidentService(db).create_resident(body)


@router.get("/{resident_id}", response_model=ResidentDetail)
def get_resident_detail(
    resident_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ResidentService(db).get_detail(resident_id)


@router.put("/{resident_id}", response_model=ResidentDetail)
def update_resident(
    resident_id: str,
    body: ResidentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ResidentService(db).update_resident(resident_id, body)


@router.post("/{resident_id}/transfer", response_model=ResidentDetail)
def transfer_resident(
    resident_id: str,
    body: ResidentTransferRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ResidentService(db).transfer_resident(resident_id, body)


@router.delete("/{resident_id}", response_model=ResidentDetail)
def delete_resident(
    resident_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ResidentService(db).delete_resident(resident_id)
