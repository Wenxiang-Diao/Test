from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.models import Alert
from app.repositories.repositories import AlertRepository, EventRepository, SummaryRepository, VitalRepository
from app.services.baseline_service import BaselineService


class AlertRuleService:
    def __init__(self, db: Session):
        self.db = db
        self.alert_repo = AlertRepository(db)
        self.event_repo = EventRepository(db)
        self.vital_repo = VitalRepository(db)
        self.summary_repo = SummaryRepository(db)
        self.baseline_service = BaselineService(db)

    def evaluate_all_residents(self) -> list[Alert]:
        from app.repositories.repositories import ResidentRepository

        created = []
        for resident in ResidentRepository(self.db).list_all():
            created.extend(self.evaluate_resident(resident.id))
        return created

    def evaluate_resident(self, resident_id: str) -> list[Alert]:
        created: list[Alert] = []
        baseline = self.baseline_service.compute(resident_id)
        latest = self.event_repo.latest_for_resident(resident_id)
        summary = self.summary_repo.latest_for_resident(resident_id)
        since = datetime.utcnow() - timedelta(hours=1)
        vitals = self.vital_repo.recent_for_resident(resident_id, since)

        if latest and latest.bed_status == "OUT_OF_BED":
            threshold = baseline.get("avg_longest_out_of_bed_30d") or 10
            out_events = self.event_repo.recent_for_resident(
                resident_id, datetime.utcnow() - timedelta(hours=4)
            )
            out_start = None
            for e in reversed(out_events):
                if e.bed_status == "OUT_OF_BED":
                    out_start = e.timestamp
                    break
            if out_start:
                duration_min = (datetime.utcnow() - out_start).total_seconds() / 60
                if duration_min > threshold * 1.5:
                    created.append(self._create(
                        resident_id, "Long out-of-bed event", "High",
                        f"Approximately {duration_min - threshold:.0f} minutes above baseline",
                        "Go and check on the resident",
                    ))

        if summary and baseline.get("avg_bed_exit_count_30d"):
            if summary.bed_exit_count > baseline["avg_bed_exit_count_30d"] * 1.5:
                created.append(self._create(
                    resident_id, "Repeated bed exits", "Medium",
                    f"{summary.bed_exit_count} bed exits tonight, above 30-day average",
                    "Monitor night-time activity pattern",
                ))

        if vitals and baseline.get("heart_rate_baseline_high"):
            abnormal = [
                v for v in vitals
                if v.heart_rate_bpm > baseline["heart_rate_baseline_high"]
                or v.heart_rate_bpm < baseline["heart_rate_baseline_low"]
            ]
            if len(abnormal) >= 3:
                created.append(self._create(
                    resident_id, "Sustained abnormal heart rate", "Medium",
                    f"{len(abnormal)} consecutive readings outside personal baseline",
                    "Check resident's physical condition",
                ))

        if latest and latest.bed_status == "NO_PERSON":
            hour = datetime.utcnow().hour
            if hour >= 22 or hour <= 6:
                created.append(self._create(
                    resident_id, "No person detected", "High",
                    "No person detected during scheduled sleep period",
                    "Go to the room immediately to confirm",
                ))

        if latest and latest.confidence < 0.5:
            created.append(self._create(
                resident_id, "Low device confidence", "Low",
                f"confidence={latest.confidence:.2f}; data quality uncertain",
                "Check device placement and connection",
            ))

        low_conf_vitals = [v for v in vitals if v.confidence < 0.5]
        if len(low_conf_vitals) >= 3:
            created.append(self._create(
                resident_id, "Device data quality issue", "Low",
                "Multiple consecutive vital-sign readings with low confidence",
                "Inspect the sensor",
            ))

        return created

    def _create(
        self, resident_id: str, alert_type: str, severity: str,
        reason: str, action: str,
    ) -> Alert:
        alert = Alert(
            resident_id=resident_id,
            alert_type=alert_type,
            severity=severity,
            reason=reason,
            suggested_action=action,
            timestamp=datetime.utcnow(),
        )
        return self.alert_repo.create(alert)
