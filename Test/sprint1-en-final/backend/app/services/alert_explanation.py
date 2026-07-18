from __future__ import annotations

from typing import Any

import pandas as pd


def explain_long_out_of_bed(duration_min: float, baseline_min: float) -> str:
    excess_min = max(duration_min - baseline_min, 0)
    ratio = duration_min / baseline_min if baseline_min else 0
    if ratio >= 2.5:
        pattern = "Critical prolonged bed exit"
        detail = (
            f"the resident has been out of bed for {duration_min:.0f} minutes, "
            f"more than {ratio:.1f} times their usual longest duration"
        )
    elif ratio >= 2:
        pattern = "Markedly prolonged bed exit"
        detail = (
            f"the resident has been out of bed about {excess_min:.0f} minutes longer "
            "than their normal pattern"
        )
    else:
        pattern = "Prolonged bed exit"
        detail = (
            f"the current out-of-bed duration is {duration_min:.0f} minutes, "
            f"above the resident's usual baseline of {baseline_min:.0f} minutes"
        )
    return _sentence("High", pattern, detail)


def explain_repeated_bed_exits(count: int, baseline_count: float) -> str:
    ratio = count / baseline_count if baseline_count else 0
    if ratio >= 2.5:
        pattern = "Very frequent night-time bed exits"
        detail = (
            f"the resident has left bed {count} times tonight, over {ratio:.1f} times "
            "their 30-day average"
        )
    elif count >= baseline_count + 3:
        pattern = "Repeated bed exits above usual pattern"
        detail = (
            f"the resident has left bed {count} times tonight, several times above "
            f"their 30-day average of {baseline_count:.1f}"
        )
    else:
        pattern = "Higher-than-usual bed-exit count"
        detail = (
            f"tonight's {count} bed exits are higher than the resident's 30-day "
            f"average of {baseline_count:.1f}"
        )
    return _sentence("Medium", pattern, detail)


def explain_abnormal_heart_rate(
    abnormal_count: int,
    latest_heart_rate: float | None,
    baseline_low: float | None,
    baseline_high: float | None,
) -> str:
    direction = _heart_rate_direction(latest_heart_rate, baseline_low, baseline_high)
    if direction == "high":
        pattern = "Sustained elevated heart rate"
        detail = (
            f"{abnormal_count} recent readings are above the resident's personal "
            f"baseline range of {baseline_low:.0f}-{baseline_high:.0f} bpm"
            if baseline_low is not None and baseline_high is not None
            else f"{abnormal_count} recent heart-rate readings are above the resident's normal range"
        )
    elif direction == "low":
        pattern = "Sustained low heart rate"
        detail = (
            f"{abnormal_count} recent readings are below the resident's personal "
            f"baseline range of {baseline_low:.0f}-{baseline_high:.0f} bpm"
            if baseline_low is not None and baseline_high is not None
            else f"{abnormal_count} recent heart-rate readings are below the resident's normal range"
        )
    else:
        pattern = "Sustained abnormal heart-rate pattern"
        detail = (
            f"{abnormal_count} recent heart-rate readings are outside the resident's "
            "personal baseline"
        )
    if latest_heart_rate is not None:
        detail = f"{detail}; the latest reading is {latest_heart_rate:.0f} bpm"
    return _sentence("Medium", pattern, detail)


def explain_no_person_detected(hour: int) -> str:
    if hour >= 22:
        pattern = "No person detected during late-night sleep hours"
        detail = "no person is detected when the resident is expected to be resting overnight"
    elif hour <= 6:
        pattern = "No person detected in the early morning sleep window"
        detail = "the bed sensor cannot detect the resident during the expected sleep period"
    else:
        pattern = "No person detected"
        detail = "the bed sensor cannot detect the resident while monitoring is active"
    return _sentence("High", pattern, detail)


def explain_low_device_confidence(confidence: float) -> str:
    if confidence < 0.3:
        pattern = "Very low bed-sensor confidence"
        detail = (
            f"the latest bed sensor confidence is only {confidence:.2f}, so the "
            "resident's current status may be unreliable"
        )
    elif confidence < 0.5:
        pattern = "Low bed-sensor confidence"
        detail = (
            f"the latest bed sensor reading has low confidence ({confidence:.2f}), "
            "so the status may be uncertain"
        )
    else:
        pattern = "Borderline bed-sensor confidence"
        detail = (
            f"the latest bed sensor confidence is {confidence:.2f}, close to the "
            "review threshold"
        )
    return _sentence("Low", pattern, detail)


def explain_vital_data_quality(confidences: list[float]) -> str:
    count = len(confidences)
    average = sum(confidences) / count if count else 0
    if average < 0.3:
        pattern = "Very low vital-sign data confidence"
        detail = (
            f"{count} recent vital-sign readings have very low confidence "
            f"(average {average:.2f}), so the sensor data may not be reliable"
        )
    elif count >= 5:
        pattern = "Repeated vital-sign data quality issue"
        detail = (
            f"{count} recent vital-sign readings have low confidence, suggesting "
            "the sensor placement or connection should be reviewed"
        )
    else:
        pattern = "Vital-sign data quality issue"
        detail = (
            "multiple recent vital-sign readings have low confidence, so the "
            "device data may need review"
        )
    return _sentence("Low", pattern, detail)


def explain_model_risk(row: pd.Series, risk_level: str = "higher") -> str:
    signals = model_risk_signals(row)
    if not signals:
        return "The system predicts low bed-exit risk because no strong pre-exit pattern was detected."

    signal_text = _join([signal["explanation"] for signal in signals[:3]])
    if risk_level == "High":
        prefix = "The system predicts high bed-exit risk"
    elif risk_level == "Medium":
        prefix = "The system predicts medium bed-exit risk"
    elif risk_level == "Low":
        prefix = "The system predicts low bed-exit risk with some minor signals"
    else:
        prefix = "The system predicts higher bed-exit risk"
    return f"{prefix} because the resident {signal_text}."


def model_risk_signals(row: pd.Series) -> list[dict[str, str]]:
    signals: list[dict[str, str]] = []
    if row.get("is_common_exit_period", 0) == 1:
        signals.append(_signal("Usual bed-exit time", "usually gets up around this time"))
    if row.get("movement_slope_10m", 0) > 0:
        signals.append(_signal("Increasing movement", "has shown increased movement in the last 10 minutes"))
    if row.get("activity_status_ACTIVE", 0) == 1 or row.get("motion_status_ACTIVE", 0) == 1:
        signals.append(_signal("Active movement state", "is currently showing active movement"))
    if row.get("sleep_status_AWAKE", 0) == 1:
        signals.append(_signal("Awake sleep status", "is currently awake"))
    if row.get("sleep_status_LIGHT_SLEEP", 0) == 1:
        signals.append(_signal("Light sleep status", "is in light sleep, when small movements are more likely"))
    if row.get("heart_rate_delta_from_daily_avg", 0) > 10:
        signals.append(_signal("Marked heart-rate increase", "has a heart rate well above their recent average"))
    elif row.get("heart_rate_delta_from_daily_avg", 0) > 5:
        signals.append(_signal("Heart-rate increase", "has a heart rate above their recent average"))
    if row.get("breathing_rate_delta_from_daily_avg", 0) > 4:
        signals.append(_signal("Marked breathing-rate increase", "has a breathing rate well above their recent average"))
    elif row.get("breathing_rate_delta_from_daily_avg", 0) > 2:
        signals.append(_signal("Breathing-rate increase", "has a breathing rate above their recent average"))
    if row.get("bed_exit_count_so_far", 0) >= 2:
        signals.append(_signal("Repeated earlier bed exits", "has already left bed multiple times tonight"))
    elif row.get("bed_exit_count_so_far", 0) > 0:
        signals.append(_signal("Earlier bed exit", "has already left bed earlier tonight"))
    if 0 <= row.get("minutes_since_last_bed_exit", 9999) <= 30:
        signals.append(_signal("Recent bed exit history", "left bed recently and may repeat the pattern"))
    if row.get("previous_night_sleep_score", 100) and row.get("previous_night_sleep_score", 100) < 65:
        signals.append(_signal("Poor previous sleep score", "had a lower sleep score on the previous night"))
    if row.get("previous_night_sleep_efficiency", 1) and row.get("previous_night_sleep_efficiency", 1) < 0.7:
        signals.append(_signal("Poor previous sleep efficiency", "had lower sleep efficiency on the previous night"))
    if row.get("previous_night_bed_exit_count", 0) >= 4:
        signals.append(_signal("Frequent previous-night exits", "had frequent bed exits on the previous night"))
    if row.get("confidence_mean", 1) < 0.7:
        signals.append(_signal("Lower sensor confidence", "has lower sensor confidence, so the risk estimate should be reviewed carefully"))
    if row.get("missing_rate_10m", 0) > 0.5 or row.get("stale_data_flag", 0) == 1:
        signals.append(_signal("Recent data gap", "has missing or stale recent sensor data"))
    return signals


def _sentence(severity: str, pattern: str, detail: str) -> str:
    return f"The system raises a {severity.lower()} alert ({pattern}) because {detail}."


def _signal(signal_type: str, explanation: str) -> dict[str, str]:
    return {"type": signal_type, "explanation": explanation}


def _join(parts: list[str]) -> str:
    if len(parts) <= 1:
        return parts[0] if parts else ""
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return f"{', '.join(parts[:-1])}, and {parts[-1]}"


def _heart_rate_direction(
    latest_heart_rate: float | None,
    baseline_low: float | None,
    baseline_high: float | None,
) -> str:
    if latest_heart_rate is None:
        return "mixed"
    if baseline_high is not None and latest_heart_rate > baseline_high:
        return "high"
    if baseline_low is not None and latest_heart_rate < baseline_low:
        return "low"
    return "mixed"
