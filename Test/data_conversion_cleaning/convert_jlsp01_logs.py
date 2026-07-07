"""Convert JLSP01 raw request logs into cleaned CSV files.

The script intentionally uses only the Python standard library so it can run in
the project environment without installing extra packages.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


DEFAULT_RESIDENT_ID = "R001"
LINE_PATTERN = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'(?P<payload>\{.*\})'$")
VALID_HR_RANGE = (30, 200)
VALID_BR_RANGE = (5, 40)
VITAL_PAIR_MAX_SECONDS = 60
RESAMPLE_SECONDS = 60


@dataclass
class DeviceState:
    resident_id: str = DEFAULT_RESIDENT_ID
    bed_status: str | None = None
    activity_status: str = "STATIC"
    latest_hr: float | None = None
    latest_hr_time: datetime | None = None
    latest_br: float | None = None
    latest_br_time: datetime | None = None
    last_vital_key: tuple[str, str] | None = None


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=root / "dataset" / "dataset",
        help="Folder containing JLSP01 *request_log*.txt files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "output",
        help="Folder where converted CSV files will be written.",
    )
    return parser.parse_args()


def build_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    input_dir = args.input_dir
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    return input_dir, output_dir


def parse_line(line: str) -> tuple[datetime, dict[str, Any]]:
    match = LINE_PATTERN.match(line.strip())
    if not match:
        raise ValueError("Line does not match expected timestamp + quoted JSON format")
    timestamp = datetime.strptime(match.group("ts"), "%Y-%m-%d %H:%M:%S")
    payload = json.loads(match.group("payload"))
    return timestamp, payload


def confidence_for(valid: bool, method: str, value: Any) -> float:
    if not valid:
        return 0.2
    if method == "motionStatus" and str(value) == "255":
        return 0.4
    return 1.0


def update_activity(value: str) -> str:
    if value == "0":
        return "NONE"
    if value == "1":
        return "STATIC"
    if value == "2":
        return "ACTIVE"
    return "UNKNOWN"


def activity_for_bed_event(activity_status: str) -> str:
    return "ACTIVE" if activity_status == "ACTIVE" else "STATIC"


def sleep_stage(value: str) -> str:
    return {
        "0": "DEEP_SLEEP",
        "1": "LIGHT_SLEEP",
        "2": "AWAKE",
        "3": "NONE",
    }.get(value, "UNKNOWN")


def breathing_status(value: str) -> str:
    return {
        "1": "NORMAL",
        "2": "TOO_HIGH",
        "3": "TOO_LOW",
        "4": "DETECTING",
    }.get(value, "UNKNOWN")


def abnormal_sleep_status(value: str) -> str:
    return {
        "0": "SLEEP_DURATION_UNDER_4_HOURS",
        "1": "SLEEP_DURATION_OVER_12_HOURS",
        "2": "LONG_NO_PERSON_DURATION",
        "3": "NONE",
    }.get(value, "UNKNOWN")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def floor_time(timestamp_text: str, seconds: int = RESAMPLE_SECONDS) -> datetime:
    timestamp = datetime.fromisoformat(timestamp_text)
    epoch = int(timestamp.timestamp())
    return datetime.fromtimestamp(epoch - (epoch % seconds))


def resample_vitals(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, datetime], dict[str, list[float]]] = defaultdict(lambda: {
        "heart_rate_bpm": [],
        "breathing_rate_per_min": [],
        "confidence": [],
    })
    for row in rows:
        key = (row["resident_id"], floor_time(row["timestamp"]))
        buckets[key]["heart_rate_bpm"].append(float(row["heart_rate_bpm"]))
        buckets[key]["breathing_rate_per_min"].append(float(row["breathing_rate_per_min"]))
        buckets[key]["confidence"].append(float(row["confidence"]))

    sampled = []
    for (resident_id, timestamp), values in sorted(buckets.items(), key=lambda item: item[0][1]):
        sampled.append({
            "resident_id": resident_id,
            "timestamp": timestamp.isoformat(sep=" "),
            "heart_rate_bpm": round(sum(values["heart_rate_bpm"]) / len(values["heart_rate_bpm"]), 1),
            "breathing_rate_per_min": round(sum(values["breathing_rate_per_min"]) / len(values["breathing_rate_per_min"]), 1),
            "confidence": round(sum(values["confidence"]) / len(values["confidence"]), 2),
        })
    return sampled


def resample_activity(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, datetime], dict[str, Any]] = defaultdict(lambda: {
        "motion_status": Counter(),
        "movement_signs": [],
        "confidence": [],
    })
    for row in rows:
        key = (row["resident_id"], floor_time(row["timestamp"]))
        if row["motion_status"]:
            buckets[key]["motion_status"][row["motion_status"]] += 1
        if row["movement_signs"] != "":
            buckets[key]["movement_signs"].append(float(row["movement_signs"]))
        buckets[key]["confidence"].append(float(row["confidence"]))

    sampled = []
    for (resident_id, timestamp), values in sorted(buckets.items(), key=lambda item: item[0][1]):
        movement = values["movement_signs"]
        confidence = values["confidence"]
        status = values["motion_status"].most_common(1)[0][0] if values["motion_status"] else "UNKNOWN"
        sampled.append({
            "resident_id": resident_id,
            "timestamp": timestamp.isoformat(sep=" "),
            "motion_status": status,
            "movement_signs": round(sum(movement) / len(movement), 1) if movement else "",
            "confidence": round(sum(confidence) / len(confidence), 2) if confidence else 0.0,
        })
    return sampled


def build_sleep_summary(
    timestamp: datetime,
    resident_id: str,
    values: list[Any],
    quality_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if len(values) < 12:
        quality_rows.append({
            "timestamp": timestamp,
            "resident_id": resident_id,
            "event_type": "invalid_sleep_quality_analysis",
            "detail": f"Expected 12 values, got {len(values)}",
            "confidence": 0.2,
        })
        return None

    ints = [int(v) for v in values[:12]]
    sleep_score = ints[0]
    total_sleep_minutes = ints[1] * 256 + ints[2]
    awake_ratio = ints[3]
    light_ratio = ints[4]
    deep_ratio = ints[5]
    out_of_bed_minutes = ints[6]
    bed_exit_count = ints[7]
    turn_count = ints[8]
    avg_breathing_rate = ints[9]
    avg_heart_rate = ints[10]
    apnea_event_count = ints[11]

    if sleep_score <= 0 or total_sleep_minutes <= 0:
        quality_rows.append({
            "timestamp": timestamp,
            "resident_id": resident_id,
            "event_type": "empty_sleep_summary",
            "detail": f"Ignored sleepQualityAnalysis={values}",
            "confidence": 0.3,
        })
        return None

    awake_minutes = round(total_sleep_minutes * awake_ratio / 100)
    light_sleep_minutes = round(total_sleep_minutes * light_ratio / 100)
    deep_sleep_minutes = round(total_sleep_minutes * deep_ratio / 100)
    sleep_efficiency = max(0.0, min(1.0, 1 - (awake_minutes / total_sleep_minutes)))

    return {
        "resident_id": resident_id,
        "date": timestamp.date().isoformat(),
        "total_sleep_minutes": total_sleep_minutes,
        "awake_minutes": awake_minutes,
        "light_sleep_minutes": light_sleep_minutes,
        "deep_sleep_minutes": deep_sleep_minutes,
        "sleep_efficiency": round(sleep_efficiency, 3),
        "sleep_score": sleep_score,
        "bed_exit_count": bed_exit_count,
        "total_out_of_bed_minutes": out_of_bed_minutes,
        "turn_count": turn_count,
        "avg_heart_rate": avg_heart_rate,
        "avg_breathing_rate": avg_breathing_rate,
        "apnea_event_count": apnea_event_count,
    }


def compute_bed_exit_stats(bed_rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, float]]:
    stats: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: {
        "bed_exit_count_from_events": 0,
        "total_out_of_bed_minutes_from_events": 0.0,
        "longest_out_of_bed_minutes": 0.0,
    })
    sorted_rows = sorted(bed_rows, key=lambda row: (row["resident_id"], row["timestamp"]))
    out_start: dict[str, datetime | None] = defaultdict(lambda: None)

    for row in sorted_rows:
        resident_id = row["resident_id"]
        timestamp = datetime.fromisoformat(row["timestamp"])
        day_key = (resident_id, timestamp.date().isoformat())
        if row["bed_status"] == "OUT_OF_BED" and out_start[resident_id] is None:
            out_start[resident_id] = timestamp
            stats[day_key]["bed_exit_count_from_events"] += 1
        elif row["bed_status"] == "IN_BED" and out_start[resident_id] is not None:
            start = out_start[resident_id]
            duration = max(0.0, (timestamp - start).total_seconds() / 60)
            start_day_key = (resident_id, start.date().isoformat())
            stats[start_day_key]["total_out_of_bed_minutes_from_events"] += duration
            stats[start_day_key]["longest_out_of_bed_minutes"] = max(
                stats[start_day_key]["longest_out_of_bed_minutes"],
                duration,
            )
            out_start[resident_id] = None

    return stats


def dedupe_bed_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority = {"NO_PERSON": 3, "OUT_OF_BED": 2, "IN_BED": 1}
    selected: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["resident_id"], row["timestamp"])
        current = selected.get(key)
        if current is None or priority.get(row["bed_status"], 0) > priority.get(current["bed_status"], 0):
            selected[key] = row
    return sorted(selected.values(), key=lambda row: row["timestamp"])


def convert(args: argparse.Namespace) -> dict[str, Any]:
    input_dir, output_dir = build_paths(args)
    files = sorted(input_dir.glob("*request_log*.txt"))
    if not files:
        raise FileNotFoundError(f"No request log files found in {input_dir}")

    states: dict[str, DeviceState] = defaultdict(DeviceState)
    bed_rows: list[dict[str, Any]] = []
    vital_rows: list[dict[str, Any]] = []
    activity_rows: list[dict[str, Any]] = []
    presence_rows: list[dict[str, Any]] = []
    sleep_stage_rows: list[dict[str, Any]] = []
    sleep_comprehensive_rows: list[dict[str, Any]] = []
    device_status_rows: list[dict[str, Any]] = []
    summary_by_day: dict[tuple[str, date], dict[str, Any]] = {}
    quality_rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {"files": {}, "method_counts": Counter(), "outputs": {}}

    for path in files:
        file_counts: Counter[str] = Counter()
        parsed = 0
        failed = 0
        first_ts: str | None = None
        last_ts: str | None = None

        for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                timestamp, payload = parse_line(line)
            except Exception as exc:
                failed += 1
                quality_rows.append({
                    "timestamp": "",
                    "resident_id": DEFAULT_RESIDENT_ID,
                    "event_type": "parse_error",
                    "detail": f"{path.name}:{line_number}: {exc}",
                    "confidence": 0.0,
                })
                continue

            parsed += 1
            first_ts = first_ts or timestamp.isoformat(sep=" ")
            last_ts = timestamp.isoformat(sep=" ")
            method = str(payload.get("method", ""))
            mac = str(payload.get("mac", "unknown"))
            params = payload.get("params") or {}
            state = states[mac]
            file_counts[method] += 1
            summary["method_counts"][method] += 1

            if method == "motionStatus":
                value = str(params.get("motionStatus", ""))
                state.activity_status = update_activity(value)
                conf = confidence_for(state.activity_status != "UNKNOWN", method, value)
                activity_rows.append({
                    "resident_id": state.resident_id,
                    "timestamp": timestamp.isoformat(sep=" "),
                    "motion_status": state.activity_status,
                    "movement_signs": "",
                    "confidence": conf,
                })
                if conf < 0.5:
                    quality_rows.append({
                        "timestamp": timestamp.isoformat(sep=" "),
                        "resident_id": state.resident_id,
                        "event_type": "invalid_motion_status",
                        "detail": f"motionStatus={value}",
                        "confidence": conf,
                    })

            elif method == "movementSigns":
                value = float(params.get("movementSigns", 0))
                activity_rows.append({
                    "resident_id": state.resident_id,
                    "timestamp": timestamp.isoformat(sep=" "),
                    "motion_status": state.activity_status,
                    "movement_signs": value,
                    "confidence": 1.0 if 0 <= value <= 100 else 0.3,
                })

            elif method == "getIntoBed":
                value = str(params.get("getIntoBed", ""))
                if value not in {"0", "1"}:
                    quality_rows.append({
                        "timestamp": timestamp.isoformat(sep=" "),
                        "resident_id": state.resident_id,
                        "event_type": "invalid_get_into_bed_status",
                        "detail": f"getIntoBed={value}",
                        "confidence": 0.2,
                    })
                    continue
                state.bed_status = "IN_BED" if value == "1" else "OUT_OF_BED"
                bed_rows.append({
                    "resident_id": state.resident_id,
                    "timestamp": timestamp.isoformat(sep=" "),
                    "bed_status": state.bed_status,
                    "activity_status": activity_for_bed_event(state.activity_status),
                    "confidence": 1.0 if state.activity_status in {"STATIC", "ACTIVE"} else 0.8,
                })

            elif method == "someoneExists":
                value = str(params.get("someoneExists", ""))
                if value in {"0", "1"}:
                    presence_rows.append({
                        "resident_id": state.resident_id,
                        "timestamp": timestamp.isoformat(sep=" "),
                        "presence_status": "PRESENT" if value == "1" else "NO_PERSON",
                        "raw_someone_exists": value,
                        "confidence": 1.0,
                    })
                else:
                    quality_rows.append({
                        "timestamp": timestamp.isoformat(sep=" "),
                        "resident_id": state.resident_id,
                        "event_type": "invalid_presence_status",
                        "detail": f"someoneExists={value}",
                        "confidence": 0.2,
                    })
                if value == "0":
                    state.bed_status = "NO_PERSON"
                    bed_rows.append({
                        "resident_id": state.resident_id,
                        "timestamp": timestamp.isoformat(sep=" "),
                        "bed_status": "NO_PERSON",
                        "activity_status": activity_for_bed_event(state.activity_status),
                        "confidence": 1.0,
                    })

            elif method in {"heartRateValue", "breathValue"}:
                if method == "heartRateValue":
                    value = float(params.get("heartRateValue", 0))
                    valid = VALID_HR_RANGE[0] <= value <= VALID_HR_RANGE[1]
                    state.latest_hr = value if valid else None
                    state.latest_hr_time = timestamp if valid else None
                    if not valid:
                        quality_rows.append({
                            "timestamp": timestamp.isoformat(sep=" "),
                            "resident_id": state.resident_id,
                            "event_type": "heart_rate_out_of_range",
                            "detail": f"heartRateValue={value}",
                            "confidence": 0.2,
                        })
                else:
                    value = float(params.get("breathValue", 0))
                    valid = VALID_BR_RANGE[0] <= value <= VALID_BR_RANGE[1]
                    state.latest_br = value if valid else None
                    state.latest_br_time = timestamp if valid else None
                    if not valid:
                        quality_rows.append({
                            "timestamp": timestamp.isoformat(sep=" "),
                            "resident_id": state.resident_id,
                            "event_type": "breathing_rate_out_of_range",
                            "detail": f"breathValue={value}",
                            "confidence": 0.2,
                        })

                if state.latest_hr is not None and state.latest_br is not None and state.latest_hr_time and state.latest_br_time:
                    age = abs((state.latest_hr_time - state.latest_br_time).total_seconds())
                    key = (state.latest_hr_time.isoformat(), state.latest_br_time.isoformat())
                    if age <= VITAL_PAIR_MAX_SECONDS and key != state.last_vital_key:
                        state.last_vital_key = key
                        vital_rows.append({
                            "resident_id": state.resident_id,
                            "timestamp": max(state.latest_hr_time, state.latest_br_time).isoformat(sep=" "),
                            "heart_rate_bpm": state.latest_hr,
                            "breathing_rate_per_min": state.latest_br,
                            "confidence": 1.0,
                        })

            elif method == "sleepStatus":
                value = str(params.get("sleepStatus", ""))
                sleep_stage_rows.append({
                    "resident_id": state.resident_id,
                    "timestamp": timestamp.isoformat(sep=" "),
                    "sleep_status": sleep_stage(value),
                    "raw_sleep_status": value,
                    "confidence": 1.0 if value in {"0", "1", "2", "3"} else 0.3,
                })

            elif method == "sleepComprehensiveStatus":
                values = params.get("sleepComprehensiveStatus", [])
                if len(values) >= 8:
                    ints = [int(v) for v in values[:8]]
                    sleep_comprehensive_rows.append({
                        "resident_id": state.resident_id,
                        "timestamp": timestamp.isoformat(sep=" "),
                        "presence": ints[0],
                        "sleep_status": sleep_stage(str(ints[1])),
                        "avg_breathing_rate": ints[2],
                        "avg_heart_rate": ints[3],
                        "turn_count": ints[4],
                        "large_body_movement_percent": ints[5],
                        "small_body_movement_percent": ints[6],
                        "apnea_event_count": ints[7],
                        "confidence": 1.0,
                    })
                else:
                    quality_rows.append({
                        "timestamp": timestamp.isoformat(sep=" "),
                        "resident_id": state.resident_id,
                        "event_type": "invalid_sleep_comprehensive_status",
                        "detail": f"Expected 8 values, got {len(values)}",
                        "confidence": 0.2,
                    })

            elif method == "sleepQualityAnalysis":
                values = params.get("sleepQualityAnalysis", [])
                built = build_sleep_summary(timestamp, state.resident_id, values, quality_rows)
                if built:
                    summary_by_day[(state.resident_id, timestamp.date())] = built

            elif method == "breathInform":
                value = str(params.get("breathInform", ""))
                status_text = breathing_status(value)
                device_status_rows.append({
                    "resident_id": state.resident_id,
                    "timestamp": timestamp.isoformat(sep=" "),
                    "event_type": "breathing_status",
                    "status": status_text,
                    "raw_value": value,
                    "confidence": 1.0 if status_text != "UNKNOWN" else 0.3,
                })
                if status_text in {"TOO_HIGH", "TOO_LOW", "DETECTING", "UNKNOWN"}:
                    quality_rows.append({
                        "timestamp": timestamp.isoformat(sep=" "),
                        "resident_id": state.resident_id,
                        "event_type": "breathing_status_issue",
                        "detail": f"breathInform={value} ({status_text})",
                        "confidence": 0.5 if status_text != "UNKNOWN" else 0.2,
                    })

            elif method == "abnormalSleep":
                value = str(params.get("abnormalSleep", ""))
                status_text = abnormal_sleep_status(value)
                device_status_rows.append({
                    "resident_id": state.resident_id,
                    "timestamp": timestamp.isoformat(sep=" "),
                    "event_type": "abnormal_sleep_status",
                    "status": status_text,
                    "raw_value": value,
                    "confidence": 1.0 if status_text != "UNKNOWN" else 0.3,
                })
                if status_text != "NONE":
                    quality_rows.append({
                        "timestamp": timestamp.isoformat(sep=" "),
                        "resident_id": state.resident_id,
                        "event_type": "abnormal_sleep_status",
                        "detail": f"abnormalSleep={value} ({status_text})",
                        "confidence": 0.6,
                    })

            elif method == "online":
                value = str(params.get("online", ""))
                device_status_rows.append({
                    "resident_id": state.resident_id,
                    "timestamp": timestamp.isoformat(sep=" "),
                    "event_type": "device_online_status",
                    "status": "ONLINE" if value == "1" else "OFFLINE" if value == "0" else "UNKNOWN",
                    "raw_value": value,
                    "confidence": 1.0 if value in {"0", "1"} else 0.3,
                })
                if value == "0":
                    quality_rows.append({
                        "timestamp": timestamp.isoformat(sep=" "),
                        "resident_id": state.resident_id,
                        "event_type": "device_offline",
                        "detail": f"mac={mac}",
                        "confidence": 0.0,
                    })

        summary["files"][path.name] = {
            "parsed": parsed,
            "failed": failed,
            "first_timestamp": first_ts,
            "last_timestamp": last_ts,
            "method_counts": dict(file_counts),
        }

    bed_rows = dedupe_bed_rows(bed_rows)
    bed_exit_stats = compute_bed_exit_stats(bed_rows)
    daily_analysis_rows = []
    for row in summary_by_day.values():
        stats_for_day = bed_exit_stats.get((row["resident_id"], row["date"]), {})
        enriched = {
            **row,
            "bed_exit_count_from_events": int(stats_for_day.get("bed_exit_count_from_events", 0)),
            "total_out_of_bed_minutes_from_events": round(stats_for_day.get("total_out_of_bed_minutes_from_events", 0.0), 1),
            "longest_out_of_bed_minutes_from_events": round(stats_for_day.get("longest_out_of_bed_minutes", 0.0), 1),
        }
        event_total = enriched["total_out_of_bed_minutes_from_events"]
        protocol_total = float(enriched["total_out_of_bed_minutes"])
        if event_total and protocol_total and abs(event_total - protocol_total) > max(10.0, protocol_total * 2):
            quality_rows.append({
                "timestamp": f"{row['date']} 00:00:00",
                "resident_id": row["resident_id"],
                "event_type": "bed_event_summary_mismatch",
                "detail": (
                    "Sparse getIntoBed events produced an out-of-bed total "
                    f"of {event_total:.1f} minutes, while sleepQualityAnalysis reports "
                    f"{protocol_total:.1f} minutes. Backend summary uses protocol total as proxy."
                ),
                "confidence": 0.5,
            })
        daily_analysis_rows.append(enriched)
    daily_analysis_rows.sort(key=lambda row: (row["resident_id"], row["date"]))

    backend_daily_rows = []
    for row in daily_analysis_rows:
        backend_daily_rows.append({
            "resident_id": row["resident_id"],
            "date": row["date"],
            "total_sleep_minutes": row["total_sleep_minutes"],
            "awake_minutes": row["awake_minutes"],
            "light_sleep_minutes": row["light_sleep_minutes"],
            "deep_sleep_minutes": row["deep_sleep_minutes"],
            "sleep_efficiency": row["sleep_efficiency"],
            "sleep_score": row["sleep_score"],
            "bed_exit_count": row["bed_exit_count"],
            "longest_out_of_bed_minutes": int(round(row["total_out_of_bed_minutes"])),
            "avg_heart_rate": row["avg_heart_rate"],
            "avg_breathing_rate": row["avg_breathing_rate"],
        })

    vital_rows = resample_vitals(vital_rows)
    activity_rows = resample_activity(activity_rows)
    presence_rows.sort(key=lambda row: row["timestamp"])
    sleep_stage_rows.sort(key=lambda row: row["timestamp"])
    sleep_comprehensive_rows.sort(key=lambda row: row["timestamp"])
    device_status_rows.sort(key=lambda row: row["timestamp"])

    write_csv(output_dir / "bed_events.csv", bed_rows, ["resident_id", "timestamp", "bed_status", "activity_status", "confidence"])
    write_csv(output_dir / "vital_samples.csv", vital_rows, ["resident_id", "timestamp", "heart_rate_bpm", "breathing_rate_per_min", "confidence"])
    write_csv(
        output_dir / "daily_sleep_summary.csv",
        backend_daily_rows,
        [
            "resident_id",
            "date",
            "total_sleep_minutes",
            "awake_minutes",
            "light_sleep_minutes",
            "deep_sleep_minutes",
            "sleep_efficiency",
            "sleep_score",
            "bed_exit_count",
            "longest_out_of_bed_minutes",
            "avg_heart_rate",
            "avg_breathing_rate",
        ],
    )
    write_csv(
        output_dir / "daily_sleep_analysis.csv",
        daily_analysis_rows,
        [
            "resident_id",
            "date",
            "sleep_score",
            "total_sleep_minutes",
            "awake_minutes",
            "light_sleep_minutes",
            "deep_sleep_minutes",
            "sleep_efficiency",
            "total_out_of_bed_minutes",
            "bed_exit_count",
            "turn_count",
            "avg_breathing_rate",
            "avg_heart_rate",
            "apnea_event_count",
            "bed_exit_count_from_events",
            "total_out_of_bed_minutes_from_events",
            "longest_out_of_bed_minutes_from_events",
        ],
    )
    write_csv(output_dir / "activity_samples.csv", activity_rows, ["resident_id", "timestamp", "motion_status", "movement_signs", "confidence"])
    write_csv(output_dir / "presence_events.csv", presence_rows, ["resident_id", "timestamp", "presence_status", "raw_someone_exists", "confidence"])
    write_csv(output_dir / "sleep_stage_samples.csv", sleep_stage_rows, ["resident_id", "timestamp", "sleep_status", "raw_sleep_status", "confidence"])
    write_csv(
        output_dir / "sleep_comprehensive_status.csv",
        sleep_comprehensive_rows,
        [
            "resident_id",
            "timestamp",
            "presence",
            "sleep_status",
            "avg_breathing_rate",
            "avg_heart_rate",
            "turn_count",
            "large_body_movement_percent",
            "small_body_movement_percent",
            "apnea_event_count",
            "confidence",
        ],
    )
    write_csv(output_dir / "device_status_events.csv", device_status_rows, ["resident_id", "timestamp", "event_type", "status", "raw_value", "confidence"])
    write_csv(output_dir / "data_quality_events.csv", quality_rows, ["timestamp", "resident_id", "event_type", "detail", "confidence"])

    summary["method_counts"] = dict(summary["method_counts"])
    summary["outputs"] = {
        "bed_events": len(bed_rows),
        "vital_samples": len(vital_rows),
        "daily_sleep_summary": len(backend_daily_rows),
        "daily_sleep_analysis": len(daily_analysis_rows),
        "activity_samples": len(activity_rows),
        "presence_events": len(presence_rows),
        "sleep_stage_samples": len(sleep_stage_rows),
        "sleep_comprehensive_status": len(sleep_comprehensive_rows),
        "device_status_events": len(device_status_rows),
        "data_quality_events": len(quality_rows),
    }
    (output_dir / "conversion_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    args = parse_args()
    summary = convert(args)
    print(json.dumps(summary["outputs"], indent=2))


if __name__ == "__main__":
    main()
