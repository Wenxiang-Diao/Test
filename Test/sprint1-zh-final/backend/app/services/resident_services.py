from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.analytics.prediction_engine import PredictionEngine
from app.repositories.repositories import (
    AlertRepository,
    EventRepository,
    PredictionRepository,
    ResidentRepository,
    SummaryRepository,
    VitalRepository,
)
from app.schemas.schemas import (
    BaselineComparison,
    BedEventItem,
    BedExitInterval,
    DashboardResponse,
    PredictionResponse,
    PredictionWindow,
    ResidentCard,
    VitalSampleItem,
)
from app.services.baseline_service import BaselineService
from app.services.bed_exit_timeline import compute_bed_exit_intervals


class ResidentService:
    def __init__(self, db: Session):
        self.db = db
        self.resident_repo = ResidentRepository(db)
        self.event_repo = EventRepository(db)
        self.alert_repo = AlertRepository(db)
        self.prediction_repo = PredictionRepository(db)
        self.baseline_service = BaselineService(db)
        self.prediction_engine = PredictionEngine()

    def list_residents(self) -> list[ResidentCard]:
        cards = []
        for resident in self.resident_repo.list_all():
            latest = self.event_repo.latest_for_resident(resident.id)
            active_count = self.alert_repo.count_active_for_resident(resident.id)
            severity = self.alert_repo.highest_active_severity(resident.id)
            latest_pred = self.prediction_repo.latest_for_resident(resident.id)
            risk = latest_pred.risk_level if latest_pred else "低"
            cards.append(
                ResidentCard(
                    id=resident.id,
                    name=resident.name,
                    bed_status=latest.bed_status if latest else "NO_PERSON",
                    activity_status=latest.activity_status if latest else None,
                    last_updated=latest.timestamp if latest else None,
                    active_alert_count=active_count,
                    highest_alert_severity=severity,
                    risk_level=risk,
                )
            )
        return cards


class DashboardService:
    def __init__(self, db: Session):
        self.resident_repo = ResidentRepository(db)
        self.event_repo = EventRepository(db)
        self.vital_repo = VitalRepository(db)
        self.summary_repo = SummaryRepository(db)
        self.baseline_service = BaselineService(db)

    def get_dashboard(self, resident_id: str) -> DashboardResponse:
        resident = self.resident_repo.get_by_id(resident_id)
        if not resident:
            raise HTTPException(status_code=404, detail="居民不存在")

        latest_event = self.event_repo.latest_for_resident(resident_id)
        summary = self.summary_repo.latest_for_resident(resident_id)
        since = datetime.utcnow() - timedelta(hours=12)
        events = self.event_repo.recent_for_resident(resident_id, since)
        vitals = self.vital_repo.recent_for_resident(resident_id, since)
        baseline = self.baseline_service.compute(resident_id)
        intervals = compute_bed_exit_intervals(
            events,
            baseline.get("avg_longest_out_of_bed_30d"),
        )

        return DashboardResponse(
            resident_id=resident.id,
            resident_name=resident.name,
            bed_status=latest_event.bed_status if latest_event else "NO_PERSON",
            bed_status_confidence=latest_event.confidence if latest_event else None,
            activity_status=latest_event.activity_status if latest_event else None,
            last_updated=latest_event.timestamp if latest_event else None,
            sleep_score=summary.sleep_score if summary else None,
            total_sleep_minutes=summary.total_sleep_minutes if summary else None,
            sleep_efficiency=summary.sleep_efficiency if summary else None,
            bed_exit_count=summary.bed_exit_count if summary else None,
            avg_heart_rate=summary.avg_heart_rate if summary else None,
            avg_breathing_rate=summary.avg_breathing_rate if summary else None,
            summary_date=summary.date if summary else None,
            bed_events=[
                BedEventItem(
                    timestamp=e.timestamp,
                    bed_status=e.bed_status,
                    activity_status=e.activity_status,
                    confidence=e.confidence,
                )
                for e in events
            ],
            bed_exit_intervals=[BedExitInterval(**i) for i in intervals],
            vital_samples=[
                VitalSampleItem(
                    timestamp=v.timestamp,
                    heart_rate_bpm=v.heart_rate_bpm,
                    breathing_rate_per_min=v.breathing_rate_per_min,
                    confidence=v.confidence,
                )
                for v in vitals
            ],
            baseline=BaselineComparison(**baseline),
        )


class PredictionService:
    def __init__(self, db: Session):
        self.resident_repo = ResidentRepository(db)
        self.event_repo = EventRepository(db)
        self.vital_repo = VitalRepository(db)
        self.summary_repo = SummaryRepository(db)
        self.prediction_repo = PredictionRepository(db)
        self.baseline_service = BaselineService(db)
        self.engine = PredictionEngine()

    def get_prediction(self, resident_id: str) -> PredictionResponse:
        if not self.resident_repo.get_by_id(resident_id):
            raise HTTPException(status_code=404, detail="居民不存在")

        latest_event = self.event_repo.latest_for_resident(resident_id)
        since = datetime.utcnow() - timedelta(hours=2)
        events = self.event_repo.recent_for_resident(resident_id, since)
        vitals = self.vital_repo.recent_for_resident(resident_id, since)
        summary = self.summary_repo.latest_for_resident(resident_id)
        baseline = self.baseline_service.compute(resident_id)

        result = self.engine.predict(
            latest_event=latest_event,
            recent_events=events,
            recent_vitals=vitals,
            summary=summary,
            baseline=baseline,
        )

        from app.models.models import Prediction

        self.prediction_repo.save(
            Prediction(
                resident_id=resident_id,
                probability=result["windows"][1]["probability"],
                risk_level=result["windows"][1]["risk_level"],
                explanation=result["explanation"],
                window_minutes=30,
            )
        )

        return PredictionResponse(
            resident_id=resident_id,
            probability=result["windows"][1]["probability"],
            risk_level=result["windows"][1]["risk_level"],
            windows=[PredictionWindow(**w) for w in result["windows"]],
            explanation=result["explanation"],
        )
