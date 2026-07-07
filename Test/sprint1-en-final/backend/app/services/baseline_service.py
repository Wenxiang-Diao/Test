from datetime import date, timedelta

import numpy as np
from sqlalchemy.orm import Session

from app.repositories.repositories import SummaryRepository


class BaselineService:
    def __init__(self, db: Session):
        self.summary_repo = SummaryRepository(db)

    def compute(self, resident_id: str, as_of_date: date | None = None) -> dict:
        today = as_of_date or date.today()
        summaries_7d = self.summary_repo.for_resident_since(
            resident_id, today - timedelta(days=7)
        )
        summaries_30d = self.summary_repo.for_resident_since(
            resident_id, today - timedelta(days=30)
        )

        def avg(items, attr):
            vals = [getattr(i, attr) for i in items if getattr(i, attr) is not None]
            return float(np.mean(vals)) if vals else None

        hr_vals = [s.avg_heart_rate for s in summaries_30d]
        br_vals = [s.avg_breathing_rate for s in summaries_30d]
        hr_mean = float(np.mean(hr_vals)) if hr_vals else None
        br_mean = float(np.mean(br_vals)) if br_vals else None
        hr_std = float(np.std(hr_vals)) if len(hr_vals) > 1 else 8.0
        br_std = float(np.std(br_vals)) if len(br_vals) > 1 else 3.0

        return {
            "avg_sleep_minutes_7d": avg(summaries_7d, "total_sleep_minutes"),
            "avg_sleep_minutes_30d": avg(summaries_30d, "total_sleep_minutes"),
            "avg_efficiency_7d": avg(summaries_7d, "sleep_efficiency"),
            "avg_efficiency_30d": avg(summaries_30d, "sleep_efficiency"),
            "avg_bed_exit_count_7d": avg(summaries_7d, "bed_exit_count"),
            "avg_bed_exit_count_30d": avg(summaries_30d, "bed_exit_count"),
            "avg_heart_rate_30d": hr_mean,
            "avg_breathing_rate_30d": br_mean,
            "heart_rate_baseline_low": hr_mean - hr_std if hr_mean else None,
            "heart_rate_baseline_high": hr_mean + hr_std if hr_mean else None,
            "breathing_rate_baseline_low": br_mean - br_std if br_mean else None,
            "breathing_rate_baseline_high": br_mean + br_std if br_mean else None,
            "avg_bed_exit_baseline_30d": avg(summaries_30d, "bed_exit_count"),
            "avg_longest_out_of_bed_30d": avg(summaries_30d, "longest_out_of_bed_minutes"),
        }
