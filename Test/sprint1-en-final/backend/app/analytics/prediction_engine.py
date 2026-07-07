from datetime import datetime

from app.models.models import BedStatusEvent, DailySleepSummary, VitalSignSample


def _risk_level(probability: float) -> str:
    if probability >= 0.65:
        return "High"
    if probability >= 0.35:
        return "Medium"
    return "Low"


class PredictionEngine:
    """Interpretable rule + statistical prediction engine (MVP; replaceable with ML module)."""

    def predict(
        self,
        latest_event: BedStatusEvent | None,
        recent_events: list[BedStatusEvent],
        recent_vitals: list[VitalSignSample],
        summary: DailySleepSummary | None,
        baseline: dict,
    ) -> dict:
        hour = datetime.utcnow().hour
        score = 0.15
        explanations: list[str] = []

        if hour >= 22 or hour <= 6:
            score += 0.15
            explanations.append("Currently within typical night-time hours")

        if latest_event and latest_event.bed_status == "OUT_OF_BED":
            score += 0.25
            explanations.append("Resident is currently out of bed")

        if len(recent_events) >= 2:
            prev, curr = recent_events[-2], recent_events[-1]
            if prev.activity_status == "STATIC" and curr.activity_status == "ACTIVE":
                score += 0.2
                explanations.append("activity_status shifted from STATIC to ACTIVE in the last 10 minutes")

        if recent_vitals and baseline.get("avg_heart_rate_30d"):
            latest_hr = recent_vitals[-1].heart_rate_bpm
            diff = latest_hr - baseline["avg_heart_rate_30d"]
            if diff > 5:
                score += min(0.15, diff / 50)
                explanations.append(f"Heart rate is approximately {diff:.0f} bpm above baseline")

        if summary and baseline.get("avg_bed_exit_count_30d"):
            if summary.bed_exit_count > baseline["avg_bed_exit_count_30d"]:
                score += 0.1
                explanations.append("Tonight's bed-exit count exceeds the 30-day average")

        score = min(max(score, 0.05), 0.95)

        windows = []
        for minutes, factor in [(15, 0.75), (30, 1.0), (60, 1.2)]:
            prob = min(score * factor, 0.98)
            windows.append({
                "minutes": minutes,
                "probability": round(prob, 2),
                "risk_level": _risk_level(prob),
            })

        if not explanations:
            explanations.append("No significant high-risk signals detected")

        explanation = "; ".join(explanations) + "."
        return {"windows": windows, "explanation": explanation}
