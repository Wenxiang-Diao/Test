from datetime import datetime

from app.models.models import BedStatusEvent


def compute_bed_exit_intervals(
    events: list[BedStatusEvent],
    baseline_longest_minutes: float | None,
) -> list[dict]:
    """从 bed_status 事件序列中提取离床区间。"""
    sorted_events = sorted(events, key=lambda e: e.timestamp)
    threshold = baseline_longest_minutes if baseline_longest_minutes else 10.0
    intervals: list[dict] = []
    out_start: datetime | None = None

    for event in sorted_events:
        if event.bed_status == "OUT_OF_BED":
            if out_start is None:
                out_start = event.timestamp
        elif out_start is not None:
            duration = (event.timestamp - out_start).total_seconds() / 60
            intervals.append(_build_interval(out_start, event.timestamp, duration, threshold))
            out_start = None

    if out_start is not None:
        now = datetime.utcnow()
        duration = (now - out_start).total_seconds() / 60
        intervals.append(_build_interval(out_start, None, duration, threshold))

    return intervals


def _build_interval(
    start: datetime,
    end: datetime | None,
    duration: float,
    threshold: float,
) -> dict:
    return {
        "start_time": start,
        "end_time": end,
        "duration_minutes": round(duration, 1),
        "exceeds_baseline": duration > threshold * 1.2,
        "baseline_minutes": round(threshold, 1),
    }
