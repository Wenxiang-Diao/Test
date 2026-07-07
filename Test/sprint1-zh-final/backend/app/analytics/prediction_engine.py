from datetime import datetime, timedelta

from app.models.models import Alert, BedStatusEvent, DailySleepSummary, VitalSignSample


def _risk_level(probability: float) -> str:
    if probability >= 0.65:
        return "高"
    if probability >= 0.35:
        return "中"
    return "低"


class PredictionEngine:
    """可解释规则 + 统计特征预测引擎（MVP，可替换为 Wenxiang ML 模块）"""

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

        # 夜间时段 (22:00 - 06:00)
        if hour >= 22 or hour <= 6:
            score += 0.15
            explanations.append("当前处于典型夜间时段")

        # 已在离床状态
        if latest_event and latest_event.bed_status == "OUT_OF_BED":
            score += 0.25
            explanations.append("居民当前处于离床状态")

        # 活动状态变化 STATIC -> ACTIVE
        if len(recent_events) >= 2:
            prev, curr = recent_events[-2], recent_events[-1]
            if prev.activity_status == "STATIC" and curr.activity_status == "ACTIVE":
                score += 0.2
                explanations.append("近 10 分钟 activity_status 由 STATIC 转为 ACTIVE")

        # 心率偏离基线
        if recent_vitals and baseline.get("avg_heart_rate_30d"):
            latest_hr = recent_vitals[-1].heart_rate_bpm
            diff = latest_hr - baseline["avg_heart_rate_30d"]
            if diff > 5:
                score += min(0.15, diff / 50)
                explanations.append(f"心率较基线偏高约 {diff:.0f} bpm")

        # 历史离床模式
        if summary and baseline.get("avg_bed_exit_count_30d"):
            if summary.bed_exit_count > baseline["avg_bed_exit_count_30d"]:
                score += 0.1
                explanations.append("今晚离床次数已高于 30 天均值")

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
            explanations.append("当前未检测到明显高风险信号")

        explanation = "；".join(explanations) + "。"
        return {"windows": windows, "explanation": explanation}
