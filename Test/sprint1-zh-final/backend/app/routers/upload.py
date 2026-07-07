from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.models import User
from app.schemas.schemas import UploadResult
from app.services.alert_service import AlertRuleService
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/bed-events", response_model=UploadResult)
async def upload_bed_events(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    count = await IngestionService(db).upload_bed_events(file)
    AlertRuleService(db).evaluate_all_residents()
    return UploadResult(inserted=count, message=f"成功导入 {count} 条离床事件")


@router.post("/vitals", response_model=UploadResult)
async def upload_vitals(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    count = await IngestionService(db).upload_vitals(file)
    AlertRuleService(db).evaluate_all_residents()
    return UploadResult(inserted=count, message=f"成功导入 {count} 条生命体征")


@router.post("/sleep-summary", response_model=UploadResult)
async def upload_sleep_summary(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    count = await IngestionService(db).upload_sleep_summary(file)
    AlertRuleService(db).evaluate_all_residents()
    return UploadResult(inserted=count, message=f"成功导入 {count} 条睡眠摘要")
