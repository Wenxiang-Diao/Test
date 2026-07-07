from datetime import datetime
from io import StringIO

import pandas as pd
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.models import BedStatusEvent, DailySleepSummary, VitalSignSample
from app.repositories.repositories import EventRepository, ResidentRepository, SummaryRepository, VitalRepository

VALID_BED_STATUS = {"IN_BED", "OUT_OF_BED", "NO_PERSON"}
VALID_ACTIVITY = {"STATIC", "ACTIVE"}


class IngestionService:
    def __init__(self, db: Session):
        self.db = db
        self.resident_repo = ResidentRepository(db)
        self.event_repo = EventRepository(db)
        self.vital_repo = VitalRepository(db)
        self.summary_repo = SummaryRepository(db)

    async def _read_csv(self, file: UploadFile) -> pd.DataFrame:
        content = await file.read()
        try:
            return pd.read_csv(StringIO(content.decode("utf-8")))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {exc}") from exc

    async def upload_bed_events(self, file: UploadFile) -> int:
        df = await self._read_csv(file)
        required = {"resident_id", "timestamp", "bed_status", "activity_status"}
        if not required.issubset(df.columns):
            raise HTTPException(status_code=400, detail=f"Missing required columns: {required - set(df.columns)}")

        events = []
        for _, row in df.iterrows():
            resident_id = str(row["resident_id"]).strip()
            if not self.resident_repo.exists(resident_id):
                raise HTTPException(status_code=400, detail=f"Resident {resident_id} does not exist")
            bed_status = str(row["bed_status"]).strip().upper()
            activity = str(row["activity_status"]).strip().upper()
            if bed_status not in VALID_BED_STATUS:
                raise HTTPException(status_code=400, detail=f"Invalid bed_status: {bed_status}")
            if activity not in VALID_ACTIVITY:
                raise HTTPException(status_code=400, detail=f"Invalid activity_status: {activity}")
            try:
                ts = pd.to_datetime(row["timestamp"]).to_pydatetime()
            except Exception as exc:
                raise HTTPException(status_code=400, detail="Invalid timestamp format") from exc
            confidence = float(row.get("confidence", 1.0))
            events.append(
                BedStatusEvent(
                    resident_id=resident_id,
                    timestamp=ts,
                    bed_status=bed_status,
                    activity_status=activity,
                    confidence=confidence,
                )
            )
        return self.event_repo.bulk_insert_bed_events(events)

    async def upload_vitals(self, file: UploadFile) -> int:
        df = await self._read_csv(file)
        required = {"resident_id", "timestamp", "heart_rate_bpm", "breathing_rate_per_min"}
        if not required.issubset(df.columns):
            raise HTTPException(status_code=400, detail=f"Missing required columns: {required - set(df.columns)}")

        samples = []
        for _, row in df.iterrows():
            resident_id = str(row["resident_id"]).strip()
            if not self.resident_repo.exists(resident_id):
                raise HTTPException(status_code=400, detail=f"Resident {resident_id} does not exist")
            hr = float(row["heart_rate_bpm"])
            br = float(row["breathing_rate_per_min"])
            if not (30 <= hr <= 200):
                raise HTTPException(status_code=400, detail=f"Heart rate out of range: {hr}")
            if not (5 <= br <= 40):
                raise HTTPException(status_code=400, detail=f"Breathing rate out of range: {br}")
            try:
                ts = pd.to_datetime(row["timestamp"]).to_pydatetime()
            except Exception as exc:
                raise HTTPException(status_code=400, detail="Invalid timestamp format") from exc
            samples.append(
                VitalSignSample(
                    resident_id=resident_id,
                    timestamp=ts,
                    heart_rate_bpm=hr,
                    breathing_rate_per_min=br,
                    confidence=float(row.get("confidence", 1.0)),
                )
            )
        return self.vital_repo.bulk_insert(samples)

    async def upload_sleep_summary(self, file: UploadFile) -> int:
        df = await self._read_csv(file)
        required = {
            "resident_id", "date", "total_sleep_minutes", "sleep_efficiency",
            "sleep_score", "bed_exit_count", "avg_heart_rate", "avg_breathing_rate",
        }
        if not required.issubset(df.columns):
            raise HTTPException(status_code=400, detail=f"Missing required columns: {required - set(df.columns)}")

        summaries = []
        for _, row in df.iterrows():
            resident_id = str(row["resident_id"]).strip()
            if not self.resident_repo.exists(resident_id):
                raise HTTPException(status_code=400, detail=f"Resident {resident_id} does not exist")
            try:
                d = pd.to_datetime(row["date"]).date()
            except Exception as exc:
                raise HTTPException(status_code=400, detail="Invalid date format") from exc
            summaries.append(
                DailySleepSummary(
                    resident_id=resident_id,
                    date=d,
                    total_sleep_minutes=int(row["total_sleep_minutes"]),
                    awake_minutes=int(row.get("awake_minutes", 0)),
                    light_sleep_minutes=int(row.get("light_sleep_minutes", 0)),
                    deep_sleep_minutes=int(row.get("deep_sleep_minutes", 0)),
                    sleep_efficiency=float(row["sleep_efficiency"]),
                    sleep_score=int(row["sleep_score"]),
                    bed_exit_count=int(row["bed_exit_count"]),
                    longest_out_of_bed_minutes=int(row.get("longest_out_of_bed_minutes", 0)),
                    avg_heart_rate=float(row["avg_heart_rate"]),
                    avg_breathing_rate=float(row["avg_breathing_rate"]),
                )
            )
        return self.summary_repo.bulk_insert(summaries)
