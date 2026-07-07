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
                        resident_id, "离床时间过长", "高",
                        f"超出基线约 {duration_min - threshold:.0f} 分钟",
                        "前往查看居民状态",
                    ))

        if summary and baseline.get("avg_bed_exit_count_30d"):
            if summary.bed_exit_count > baseline["avg_bed_exit_count_30d"] * 1.5:
                created.append(self._create(
                    resident_id, "离床次数异常", "中",
                    f"今晚离床 {summary.bed_exit_count} 次，高于 30 天均值",
                    "关注夜间活动模式",
                ))

        if vitals and baseline.get("heart_rate_baseline_high"):
            abnormal = [
                v for v in vitals
                if v.heart_rate_bpm > baseline["heart_rate_baseline_high"]
                or v.heart_rate_bpm < baseline["heart_rate_baseline_low"]
            ]
            if len(abnormal) >= 3:
                created.append(self._create(
                    resident_id, "心率持续偏高", "中",
                    f"连续 {len(abnormal)} 条读数偏离个体基线",
                    "检查居民身体状况",
                ))

        if latest and latest.bed_status == "NO_PERSON":
            hour = datetime.utcnow().hour
            if hour >= 22 or hour <= 6:
                created.append(self._create(
                    resident_id, "未检测到人员", "高",
                    "睡眠时段未检测到居民",
                    "立即前往房间确认",
                ))

        if latest and latest.confidence < 0.5:
            created.append(self._create(
                resident_id, "设备置信度低", "低",
                f"confidence={latest.confidence:.2f}，数据质量存疑",
                "检查设备位置与连接",
            ))

        low_conf_vitals = [v for v in vitals if v.confidence < 0.5]
        if len(low_conf_vitals) >= 3:
            created.append(self._create(
                resident_id, "设备数据质量", "低",
                "连续多条生命体征读数置信度过低",
                "检查传感器",
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
