"""Import cleaned JLSP01 CSV outputs into the dashboard database."""

from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine
from app.models.models import BedStatusEvent, DailySleepSummary, Device, Resident, VitalSignSample


def ensure_resident_profile_columns() -> None:
    columns = {
        "medical_history": "TEXT",
        "daily_habits": "TEXT",
        "care_notes": "TEXT",
        "monitoring_status": "VARCHAR(24) NOT NULL DEFAULT 'ACTIVE'",
        "room_number": "VARCHAR(32)",
        "building": "VARCHAR(64)",
        "floor_level": "VARCHAR(32)",
        "location_notes": "TEXT",
        "transfer_destination": "VARCHAR(128)",
        "transfer_date": "DATE",
    }
    with engine.begin() as conn:
        for column, ddl_type in columns.items():
            conn.execute(text(f"ALTER TABLE residents ADD COLUMN IF NOT EXISTS {column} {ddl_type}"))


def default_input_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data_conversion_cleaning" / "output_verified"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def ensure_resident_and_device(db, resident_id: str) -> None:
    resident = db.query(Resident).filter(Resident.id == resident_id).first()
    if not resident:
        db.add(
            Resident(
                id=resident_id,
                name=f"Resident {resident_id}",
                monitoring_status="ACTIVE",
                room_number="Imported",
                building="JLSP01 Demo",
                floor_level="",
                location_notes="Imported from cleaned JLSP01 request logs.",
            )
        )
        db.commit()
    device_id = f"JLSP01-{resident_id}"
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        db.add(Device(device_id=device_id, resident_id=resident_id))
        db.commit()


def import_bed_events(db, rows: list[dict[str, str]]) -> int:
    inserted = 0
    for row in rows:
        resident_id = row["resident_id"]
        ensure_resident_and_device(db, resident_id)
        timestamp = datetime.fromisoformat(row["timestamp"])
        exists = (
            db.query(BedStatusEvent.id)
            .filter(
                BedStatusEvent.resident_id == resident_id,
                BedStatusEvent.timestamp == timestamp,
                BedStatusEvent.bed_status == row["bed_status"],
            )
            .first()
        )
        if exists:
            continue
        db.add(
            BedStatusEvent(
                resident_id=resident_id,
                timestamp=timestamp,
                bed_status=row["bed_status"],
                activity_status=row["activity_status"],
                confidence=float(row.get("confidence") or 1.0),
            )
        )
        inserted += 1
    db.commit()
    return inserted


def import_vitals(db, rows: list[dict[str, str]]) -> int:
    inserted = 0
    for row in rows:
        resident_id = row["resident_id"]
        ensure_resident_and_device(db, resident_id)
        timestamp = datetime.fromisoformat(row["timestamp"])
        exists = (
            db.query(VitalSignSample.id)
            .filter(VitalSignSample.resident_id == resident_id, VitalSignSample.timestamp == timestamp)
            .first()
        )
        if exists:
            continue
        db.add(
            VitalSignSample(
                resident_id=resident_id,
                timestamp=timestamp,
                heart_rate_bpm=float(row["heart_rate_bpm"]),
                breathing_rate_per_min=float(row["breathing_rate_per_min"]),
                confidence=float(row.get("confidence") or 1.0),
            )
        )
        inserted += 1
    db.commit()
    return inserted


def import_sleep_summary(db, rows: list[dict[str, str]]) -> int:
    inserted = 0
    for row in rows:
        resident_id = row["resident_id"]
        ensure_resident_and_device(db, resident_id)
        summary_date = datetime.fromisoformat(row["date"]).date()
        exists = (
            db.query(DailySleepSummary.id)
            .filter(DailySleepSummary.resident_id == resident_id, DailySleepSummary.date == summary_date)
            .first()
        )
        if exists:
            continue
        db.add(
            DailySleepSummary(
                resident_id=resident_id,
                date=summary_date,
                total_sleep_minutes=int(row["total_sleep_minutes"]),
                awake_minutes=int(row.get("awake_minutes") or 0),
                light_sleep_minutes=int(row.get("light_sleep_minutes") or 0),
                deep_sleep_minutes=int(row.get("deep_sleep_minutes") or 0),
                sleep_efficiency=float(row["sleep_efficiency"]),
                sleep_score=int(row["sleep_score"]),
                bed_exit_count=int(row["bed_exit_count"]),
                longest_out_of_bed_minutes=int(row.get("longest_out_of_bed_minutes") or 0),
                avg_heart_rate=float(row["avg_heart_rate"]),
                avg_breathing_rate=float(row["avg_breathing_rate"]),
            )
        )
        inserted += 1
    db.commit()
    return inserted


def main() -> None:
    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else default_input_dir()
    Base.metadata.create_all(bind=engine)
    ensure_resident_profile_columns()

    db = SessionLocal()
    try:
        counts = {
            "bed_events": import_bed_events(db, read_csv(input_dir / "bed_events.csv")),
            "vital_samples": import_vitals(db, read_csv(input_dir / "vital_samples.csv")),
            "daily_sleep_summary": import_sleep_summary(db, read_csv(input_dir / "daily_sleep_summary.csv")),
        }
        print(counts)
    finally:
        db.close()


if __name__ == "__main__":
    main()
