from datetime import date, datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ResidentCard(BaseModel):
    id: str
    name: str
    monitoring_status: str = "ACTIVE"
    room_number: str | None = None
    building: str | None = None
    floor_level: str | None = None
    bed_status: str
    activity_status: str | None = None
    last_updated: datetime | None = None
    active_alert_count: int = 0
    highest_alert_severity: str | None = None
    risk_level: str = "Low"

    model_config = {"from_attributes": True}


class ResidentBase(BaseModel):
    name: str
    medical_history: str | None = None
    daily_habits: str | None = None
    care_notes: str | None = None
    monitoring_status: str = "ACTIVE"
    room_number: str | None = None
    building: str | None = None
    floor_level: str | None = None
    location_notes: str | None = None


class ResidentCreate(ResidentBase):
    id: str


class ResidentUpdate(BaseModel):
    name: str | None = None
    medical_history: str | None = None
    daily_habits: str | None = None
    care_notes: str | None = None
    monitoring_status: str | None = None
    room_number: str | None = None
    building: str | None = None
    floor_level: str | None = None
    location_notes: str | None = None


class ResidentTransferRequest(BaseModel):
    transfer_destination: str
    transfer_date: date | None = None
    location_notes: str | None = None


class ResidentDetail(ResidentBase):
    id: str
    transfer_destination: str | None = None
    transfer_date: date | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BedExitInterval(BaseModel):
    start_time: datetime
    end_time: datetime | None = None
    duration_minutes: float
    exceeds_baseline: bool = False
    baseline_minutes: float | None = None


class BedEventItem(BaseModel):
    timestamp: datetime
    bed_status: str
    activity_status: str
    confidence: float


class VitalSampleItem(BaseModel):
    timestamp: datetime
    heart_rate_bpm: float
    breathing_rate_per_min: float
    confidence: float


class BaselineComparison(BaseModel):
    avg_sleep_minutes_7d: float | None = None
    avg_sleep_minutes_30d: float | None = None
    avg_efficiency_7d: float | None = None
    avg_efficiency_30d: float | None = None
    avg_bed_exit_count_7d: float | None = None
    avg_bed_exit_count_30d: float | None = None
    avg_heart_rate_30d: float | None = None
    avg_breathing_rate_30d: float | None = None
    heart_rate_baseline_low: float | None = None
    heart_rate_baseline_high: float | None = None
    breathing_rate_baseline_low: float | None = None
    breathing_rate_baseline_high: float | None = None


class DashboardResponse(BaseModel):
    resident_id: str
    resident_name: str
    monitoring_status: str = "ACTIVE"
    room_number: str | None = None
    building: str | None = None
    floor_level: str | None = None
    location_notes: str | None = None
    bed_status: str
    bed_status_confidence: float | None = None
    activity_status: str | None = None
    last_updated: datetime | None = None
    sleep_score: int | None = None
    total_sleep_minutes: int | None = None
    awake_minutes: int | None = None
    light_sleep_minutes: int | None = None
    deep_sleep_minutes: int | None = None
    sleep_efficiency: float | None = None
    bed_exit_count: int | None = None
    longest_out_of_bed_minutes: int | None = None
    avg_heart_rate: float | None = None
    avg_breathing_rate: float | None = None
    summary_date: date | None = None
    bed_events: list[BedEventItem] = Field(default_factory=list)
    bed_exit_intervals: list[BedExitInterval] = Field(default_factory=list)
    vital_samples: list[VitalSampleItem] = Field(default_factory=list)
    baseline: BaselineComparison | None = None
    disclaimer: str = "System output is for care decision support only and is not a medical diagnosis."


class PredictionWindow(BaseModel):
    minutes: int
    probability: float
    risk_level: str


class PredictionResponse(BaseModel):
    resident_id: str
    probability: float
    risk_level: str
    windows: list[PredictionWindow]
    explanation: str
    disclaimer: str = "System output is for care decision support only and is not a medical diagnosis."


class AlertItem(BaseModel):
    id: int
    resident_id: str
    resident_name: str
    alert_type: str
    severity: str
    reason: str
    timestamp: datetime
    suggested_action: str
    acknowledged: bool

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    alerts: list[AlertItem]
    total: int


class UploadResult(BaseModel):
    inserted: int
    message: str


class DailyReportItem(BaseModel):
    date: date
    sleep_score: int
    total_sleep_minutes: int
    awake_minutes: int
    sleep_efficiency: float
    bed_exit_count: int
    longest_out_of_bed_minutes: int
    avg_heart_rate: float
    avg_breathing_rate: float


class WeeklyTrendPoint(BaseModel):
    date: date
    total_sleep_minutes: int
    sleep_efficiency: float
    bed_exit_count: int
    avg_heart_rate: float
    avg_breathing_rate: float
    baseline_sleep_minutes: float | None = None
    baseline_efficiency: float | None = None
    baseline_bed_exit_count: float | None = None
    baseline_heart_rate: float | None = None
    baseline_breathing_rate: float | None = None


class ReportResponse(BaseModel):
    resident_id: str
    resident_name: str
    daily: DailyReportItem | None = None
    weekly: list[WeeklyTrendPoint] = Field(default_factory=list)
    disclaimer: str = "System output is for care decision support only and is not a medical diagnosis."
