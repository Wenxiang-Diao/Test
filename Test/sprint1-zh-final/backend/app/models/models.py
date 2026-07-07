from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Resident(Base):
    __tablename__ = "residents"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    devices: Mapped[list["Device"]] = relationship(back_populates="resident")
    bed_events: Mapped[list["BedStatusEvent"]] = relationship(back_populates="resident")
    vitals: Mapped[list["VitalSignSample"]] = relationship(back_populates="resident")
    summaries: Mapped[list["DailySleepSummary"]] = relationship(back_populates="resident")
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="resident")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="resident")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    resident_id: Mapped[str] = mapped_column(ForeignKey("residents.id"), nullable=False)

    resident: Mapped["Resident"] = relationship(back_populates="devices")


class BedStatusEvent(Base):
    __tablename__ = "bed_status_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resident_id: Mapped[str] = mapped_column(ForeignKey("residents.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    bed_status: Mapped[str] = mapped_column(String(32), nullable=False)
    activity_status: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    resident: Mapped["Resident"] = relationship(back_populates="bed_events")


class VitalSignSample(Base):
    __tablename__ = "vital_sign_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resident_id: Mapped[str] = mapped_column(ForeignKey("residents.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    heart_rate_bpm: Mapped[float] = mapped_column(Float, nullable=False)
    breathing_rate_per_min: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    resident: Mapped["Resident"] = relationship(back_populates="vitals")


class DailySleepSummary(Base):
    __tablename__ = "daily_sleep_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resident_id: Mapped[str] = mapped_column(ForeignKey("residents.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    total_sleep_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    awake_minutes: Mapped[int] = mapped_column(Integer, default=0)
    light_sleep_minutes: Mapped[int] = mapped_column(Integer, default=0)
    deep_sleep_minutes: Mapped[int] = mapped_column(Integer, default=0)
    sleep_efficiency: Mapped[float] = mapped_column(Float, nullable=False)
    sleep_score: Mapped[int] = mapped_column(Integer, nullable=False)
    bed_exit_count: Mapped[int] = mapped_column(Integer, default=0)
    longest_out_of_bed_minutes: Mapped[int] = mapped_column(Integer, default=0)
    avg_heart_rate: Mapped[float] = mapped_column(Float, nullable=False)
    avg_breathing_rate: Mapped[float] = mapped_column(Float, nullable=False)

    resident: Mapped["Resident"] = relationship(back_populates="summaries")


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resident_id: Mapped[str] = mapped_column(ForeignKey("residents.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    window_minutes: Mapped[int] = mapped_column(Integer, default=30)

    resident: Mapped["Resident"] = relationship(back_populates="predictions")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resident_id: Mapped[str] = mapped_column(ForeignKey("residents.id"), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_action: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)

    resident: Mapped["Resident"] = relationship(back_populates="alerts")
