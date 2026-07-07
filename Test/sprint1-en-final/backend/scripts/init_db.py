"""Initialize database and seed demo data."""
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app.models.models import (
    Alert,
    BedStatusEvent,
    DailySleepSummary,
    Device,
    Resident,
    User,
    VitalSignSample,
)
from app.services.alert_service import AlertRuleService


def ensure_resident_profile_columns():
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


def seed(reset: bool = False):
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    ensure_resident_profile_columns()
    db = SessionLocal()
    try:
        if db.query(User).first() and not reset:
            print("Database already seeded. Use --reset to rebuild.")
            return

        admin = User(username="admin", password_hash=hash_password("admin123"))
        db.add(admin)

        residents = [
            Resident(
                id="R001",
                name="Resident R001",
                medical_history="Hypertension; history of poor sleep quality.",
                daily_habits="Usually sleeps from 21:30 to 06:00; wakes once overnight.",
                care_notes="Prefers low night lighting and needs assistance after prolonged bed exits.",
                room_number="A-101",
                building="North Wing",
                floor_level="1",
                location_notes="Close to nurses' station.",
            ),
            Resident(
                id="R002",
                name="Resident R002",
                medical_history="Mild mobility limitation.",
                daily_habits="Often leaves bed around 03:00 for bathroom routine.",
                care_notes="Monitor repeated active movement after midnight.",
                room_number="B-214",
                building="East Wing",
                floor_level="2",
                location_notes="Shared corridor near lift.",
            ),
            Resident(
                id="R003",
                name="Resident R003",
                medical_history="No clinical notes in demo data.",
                daily_habits="Irregular sleep pattern in demo scenario.",
                care_notes="Device confidence is intentionally low for demo data-quality review.",
                room_number="C-305",
                building="South Wing",
                floor_level="3",
                location_notes="Temporary observation room.",
            ),
        ]
        db.add_all(residents)
        for r in residents:
            db.add(Device(device_id=f"DEV-{r.id}", resident_id=r.id))
        db.commit()

        base_date = date(2026, 6, 9)
        for i, rid in enumerate(["R001", "R002", "R003"]):
            for day_offset in range(30):
                d = base_date - timedelta(days=day_offset)
                db.add(
                    DailySleepSummary(
                        resident_id=rid,
                        date=d,
                        total_sleep_minutes=420 + (i * 10) - day_offset,
                        awake_minutes=40 + day_offset % 5,
                        light_sleep_minutes=250,
                        deep_sleep_minutes=130,
                        sleep_efficiency=0.82 + (0.01 * (day_offset % 3)),
                        sleep_score=75 + (i * 2) - (day_offset % 4),
                        bed_exit_count=2 + (day_offset % 3),
                        longest_out_of_bed_minutes=10 + day_offset % 5,
                        avg_heart_rate=70 + i * 2,
                        avg_breathing_rate=15 + i,
                    )
                )

        now = datetime.utcnow()
        bed_events = [
            ("R001", now - timedelta(hours=4), "IN_BED", "STATIC", 0.91),
            ("R001", now - timedelta(hours=2), "OUT_OF_BED", "ACTIVE", 0.88),
            ("R001", now - timedelta(hours=1, minutes=50), "IN_BED", "STATIC", 0.90),
            ("R001", now - timedelta(minutes=30), "IN_BED", "STATIC", 0.92),
            ("R001", now - timedelta(minutes=10), "IN_BED", "ACTIVE", 0.89),
            ("R002", now - timedelta(hours=3), "IN_BED", "STATIC", 0.85),
            ("R002", now - timedelta(hours=1), "OUT_OF_BED", "ACTIVE", 0.87),
            ("R002", now - timedelta(minutes=12), "OUT_OF_BED", "ACTIVE", 0.86),
            ("R003", now - timedelta(hours=2), "NO_PERSON", "STATIC", 0.45),
            ("R003", now - timedelta(minutes=20), "NO_PERSON", "STATIC", 0.42),
        ]
        for rid, ts, bed, act, conf in bed_events:
            db.add(
                BedStatusEvent(
                    resident_id=rid,
                    timestamp=ts,
                    bed_status=bed,
                    activity_status=act,
                    confidence=conf,
                )
            )

        for rid, hr_base in [("R001", 72), ("R002", 78), ("R003", 68)]:
            for m in range(0, 120, 10):
                ts = now - timedelta(minutes=120 - m)
                db.add(
                    VitalSignSample(
                        resident_id=rid,
                        timestamp=ts,
                        heart_rate_bpm=hr_base + (m % 15) - 5,
                        breathing_rate_per_min=15 + (m % 5),
                        confidence=0.88 if rid != "R003" else 0.45,
                    )
                )

        db.commit()
        AlertRuleService(db).evaluate_all_residents()
        print("Database initialized successfully")
        print("  Account: admin / admin123")
        print("  Residents: R001, R002, R003")
    finally:
        db.close()


if __name__ == "__main__":
    force = "--reset" in sys.argv
    seed(reset=force)
