from datetime import date, datetime, timedelta

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.models import (
    Alert,
    BedStatusEvent,
    DailySleepSummary,
    Prediction,
    Resident,
    VitalSignSample,
)


class ResidentRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> list[Resident]:
        return self.db.query(Resident).order_by(Resident.id).all()

    def get_by_id(self, resident_id: str) -> Resident | None:
        return self.db.query(Resident).filter(Resident.id == resident_id).first()

    def exists(self, resident_id: str) -> bool:
        return self.db.query(Resident.id).filter(Resident.id == resident_id).first() is not None


class EventRepository:
    def __init__(self, db: Session):
        self.db = db

    def bulk_insert_bed_events(self, events: list[BedStatusEvent]) -> int:
        self.db.add_all(events)
        self.db.commit()
        return len(events)

    def latest_for_resident(self, resident_id: str) -> BedStatusEvent | None:
        return (
            self.db.query(BedStatusEvent)
            .filter(BedStatusEvent.resident_id == resident_id)
            .order_by(desc(BedStatusEvent.timestamp))
            .first()
        )

    def recent_for_resident(self, resident_id: str, since: datetime) -> list[BedStatusEvent]:
        return (
            self.db.query(BedStatusEvent)
            .filter(
                BedStatusEvent.resident_id == resident_id,
                BedStatusEvent.timestamp >= since,
            )
            .order_by(BedStatusEvent.timestamp)
            .all()
        )


class VitalRepository:
    def __init__(self, db: Session):
        self.db = db

    def bulk_insert(self, samples: list[VitalSignSample]) -> int:
        self.db.add_all(samples)
        self.db.commit()
        return len(samples)

    def recent_for_resident(self, resident_id: str, since: datetime) -> list[VitalSignSample]:
        return (
            self.db.query(VitalSignSample)
            .filter(
                VitalSignSample.resident_id == resident_id,
                VitalSignSample.timestamp >= since,
            )
            .order_by(VitalSignSample.timestamp)
            .all()
        )


class SummaryRepository:
    def __init__(self, db: Session):
        self.db = db

    def bulk_insert(self, summaries: list[DailySleepSummary]) -> int:
        self.db.add_all(summaries)
        self.db.commit()
        return len(summaries)

    def latest_for_resident(self, resident_id: str) -> DailySleepSummary | None:
        return (
            self.db.query(DailySleepSummary)
            .filter(DailySleepSummary.resident_id == resident_id)
            .order_by(desc(DailySleepSummary.date))
            .first()
        )

    def for_resident_since(self, resident_id: str, since: date) -> list[DailySleepSummary]:
        return (
            self.db.query(DailySleepSummary)
            .filter(
                DailySleepSummary.resident_id == resident_id,
                DailySleepSummary.date >= since,
            )
            .order_by(DailySleepSummary.date)
            .all()
        )

    def get_by_date(self, resident_id: str, target_date: date) -> DailySleepSummary | None:
        return (
            self.db.query(DailySleepSummary)
            .filter(
                DailySleepSummary.resident_id == resident_id,
                DailySleepSummary.date == target_date,
            )
            .first()
        )


class AlertRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, alert: Alert) -> Alert:
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def list_for_resident(self, resident_id: str, limit: int = 50) -> list[Alert]:
        return (
            self.db.query(Alert)
            .filter(Alert.resident_id == resident_id)
            .order_by(desc(Alert.timestamp))
            .limit(limit)
            .all()
        )

    def list_all(self, limit: int = 100) -> list[Alert]:
        return self.db.query(Alert).order_by(desc(Alert.timestamp)).limit(limit).all()

    def count_active_for_resident(self, resident_id: str) -> int:
        return (
            self.db.query(func.count(Alert.id))
            .filter(Alert.resident_id == resident_id, Alert.acknowledged.is_(False))
            .scalar()
            or 0
        )

    def highest_active_severity(self, resident_id: str) -> str | None:
        active = (
            self.db.query(Alert)
            .filter(Alert.resident_id == resident_id, Alert.acknowledged.is_(False))
            .all()
        )
        if not active:
            return None
        order = {"高": 3, "中": 2, "低": 1}
        return max(active, key=lambda a: order.get(a.severity, 0)).severity

    def get_by_id(self, alert_id: int) -> Alert | None:
        return self.db.query(Alert).filter(Alert.id == alert_id).first()

    def acknowledge(self, alert_id: int) -> Alert | None:
        alert = self.get_by_id(alert_id)
        if alert:
            alert.acknowledged = True
            self.db.commit()
            self.db.refresh(alert)
        return alert


class PredictionRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, prediction: Prediction) -> Prediction:
        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        return prediction

    def latest_for_resident(self, resident_id: str) -> Prediction | None:
        return (
            self.db.query(Prediction)
            .filter(Prediction.resident_id == resident_id)
            .order_by(desc(Prediction.timestamp))
            .first()
        )
