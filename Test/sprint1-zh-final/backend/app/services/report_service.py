from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.repositories import ResidentRepository, SummaryRepository
from app.schemas.schemas import DailyReportItem, ReportResponse, WeeklyTrendPoint
from app.services.baseline_service import BaselineService


class ReportService:
    def __init__(self, db: Session):
        self.resident_repo = ResidentRepository(db)
        self.summary_repo = SummaryRepository(db)
        self.baseline_service = BaselineService(db)

    def get_report(self, resident_id: str, target_date: date | None = None) -> ReportResponse:
        resident = self.resident_repo.get_by_id(resident_id)
        if not resident:
            raise HTTPException(status_code=404, detail="居民不存在")

        if target_date is None:
            latest = self.summary_repo.latest_for_resident(resident_id)
            target_date = latest.date if latest else date.today()

        daily_row = self.summary_repo.get_by_date(resident_id, target_date)
        daily = None
        if daily_row:
            daily = DailyReportItem(
                date=daily_row.date,
                sleep_score=daily_row.sleep_score,
                total_sleep_minutes=daily_row.total_sleep_minutes,
                awake_minutes=daily_row.awake_minutes,
                sleep_efficiency=daily_row.sleep_efficiency,
                bed_exit_count=daily_row.bed_exit_count,
                longest_out_of_bed_minutes=daily_row.longest_out_of_bed_minutes,
                avg_heart_rate=daily_row.avg_heart_rate,
                avg_breathing_rate=daily_row.avg_breathing_rate,
            )

        since = target_date - timedelta(days=6)
        weekly_rows = self.summary_repo.for_resident_since(resident_id, since)
        baseline = self.baseline_service.compute(resident_id)

        weekly = [
            WeeklyTrendPoint(
                date=r.date,
                total_sleep_minutes=r.total_sleep_minutes,
                sleep_efficiency=r.sleep_efficiency,
                bed_exit_count=r.bed_exit_count,
                avg_heart_rate=r.avg_heart_rate,
                avg_breathing_rate=r.avg_breathing_rate,
                baseline_sleep_minutes=baseline.get("avg_sleep_minutes_30d"),
                baseline_efficiency=baseline.get("avg_efficiency_30d"),
                baseline_bed_exit_count=baseline.get("avg_bed_exit_count_30d"),
                baseline_heart_rate=baseline.get("avg_heart_rate_30d"),
                baseline_breathing_rate=baseline.get("avg_breathing_rate_30d"),
            )
            for r in weekly_rows
        ]

        return ReportResponse(
            resident_id=resident.id,
            resident_name=resident.name,
            daily=daily,
            weekly=weekly,
        )
