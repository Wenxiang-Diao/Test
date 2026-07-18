from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.models import Alert
from app.repositories.repositories import AlertRepository, EventRepository, SummaryRepository, VitalRepository
from app.services.alert_explanation import (
    explain_abnormal_heart_rate,
    explain_long_out_of_bed,
    explain_low_device_confidence,
    explain_no_person_detected,
    explain_repeated_bed_exits,
    explain_vital_data_quality,
)
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
                        explain_long_out_of_bed(duration_min, threshold),
                        "Go and check on the resident",
                    ))

        if summary and baseline.get("avg_bed_exit_count_30d"):
            if summary.bed_exit_count > baseline["avg_bed_exit_count_30d"] * 1.5:
                created.append(self._create(
                    resident_id, "Repeated bed exits", "Medium",
                    explain_repeated_bed_exits(
                        summary.bed_exit_count,
                        baseline["avg_bed_exit_count_30d"],
                    ),
                    "Monitor night-time activity pattern",
                ))

        if vitals and baseline.get("heart_rate_baseline_high"):
            abnormal = [
                v for v in vitals
                if v.heart_rate_bpm > baseline["heart_rate_baseline_high"]
                or v.heart_rate_bpm < baseline["heart_rate_baseline_low"]
            ]
            if len(abnormal) >= 3:
                latest_abnormal = abnormal[-1]
                created.append(self._create(
                    resident_id, "Sustained abnormal heart rate", "Medium",
                    explain_abnormal_heart_rate(
                        abnormal_count=len(abnormal),
                        latest_heart_rate=latest_abnormal.heart_rate_bpm,
                        baseline_low=baseline.get("heart_rate_baseline_low"),
                        baseline_high=baseline.get("heart_rate_baseline_high"),
                    ),
                    "Check resident's physical condition",
                ))

        if latest and latest.bed_status == "NO_PERSON":
            hour = datetime.utcnow().hour
            if hour >= 22 or hour <= 6:
                created.append(self._create(
                    resident_id, "No person detected", "High",
                    explain_no_person_detected(hour),
                    "Go to the room immediately to confirm",
                ))

        if latest and latest.confidence < 0.5:
            created.append(self._create(
                resident_id, "Low device confidence", "Low",
                explain_low_device_confidence(latest.confidence),
                "Check device placement and connection",
            ))

        low_conf_vitals = [v for v in vitals if v.confidence < 0.5]
        if len(low_conf_vitals) >= 3:
            created.append(self._create(
                resident_id, "Device data quality issue", "Low",
                explain_vital_data_quality([v.confidence for v in low_conf_vitals]),
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
