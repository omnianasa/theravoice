"""SQLAlchemy 2 ORM models."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    TypeDecorator,
    false,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """A DateTime that is always timezone-aware UTC, round-trip-safe on SQLite.

    SQLite has no native timezone-aware datetime type: even with
    `DateTime(timezone=True)`, values read back from a SQLite database lose
    their `tzinfo` and become naive, which then raises
    `TypeError: can't compare offset-naive and offset-aware datetimes` the
    moment that value is compared against any of the timezone-aware
    datetimes used everywhere else in this project (all timestamps here are
    always constructed as `datetime.now(timezone.utc)` or similar).

    This type stores everything normalized to UTC and, on the way back out,
    re-attaches `tzinfo=UTC` if the driver dropped it -- restoring exactly
    the value that was written, aware, every time. It's a drop-in swap for
    `DateTime(timezone=True)` in every model below and works the same way on
    any other backend that *does* preserve timezone info.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String)
    password_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)


class UserSessionModel(Base):
    __tablename__ = "user_sessions"

    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)


class PatientModel(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_user_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id"), nullable=True, index=True
    )
    display_name: Mapped[str] = mapped_column(String)
    timezone: Mapped[str] = mapped_column(String, default="UTC")
    consent_audio_analysis: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_data_storage: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_llm_processing: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)


class AudioSegmentModel(Base):
    __tablename__ = "audio_segments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.id"))
    path: Mapped[str | None] = mapped_column(String, nullable=True)
    sample_rate: Mapped[int] = mapped_column(Integer)
    duration_seconds: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
    source: Mapped[str] = mapped_column(String, default="unknown")


class TranscriptSegmentModel(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.id"))
    text: Mapped[str] = mapped_column(Text)
    start_time: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class BiomarkerModel(Base):
    __tablename__ = "biomarkers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.id"))
    name: Mapped[str] = mapped_column(String)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    reason_unavailable: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)


class BaselineStatisticModel(Base):
    __tablename__ = "baseline_statistics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.id"))
    metric_name: Mapped[str] = mapped_column(String)
    mean: Mapped[float] = mapped_column(Float)
    std: Mapped[float] = mapped_column(Float)
    n: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)


class EventModel(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.id"))
    type: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)


class ActionModel(Base):
    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.id"))
    type: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String, default="normal")
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    action_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)


class MedicationModel(Base):
    __tablename__ = "medications"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.id"))
    name: Mapped[str] = mapped_column(String)
    dosage: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class MedicationScheduleModel(Base):
    __tablename__ = "medication_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    medication_id: Mapped[str] = mapped_column(String, ForeignKey("medications.id"))
    scheduled_time: Mapped[str] = mapped_column(String)
    timezone: Mapped[str] = mapped_column(String, default="UTC")
    days_of_week: Mapped[list] = mapped_column(JSON, default=list)


class MedicationEventModel(Base):
    __tablename__ = "medication_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.id"))
    medication_id: Mapped[str] = mapped_column(String, ForeignKey("medications.id"))
    taken_at: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="unknown")


class TherapyExerciseModel(Base):
    __tablename__ = "therapy_exercises"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    instructions: Mapped[list] = mapped_column(JSON, default=list)
    clinician_approved: Mapped[bool] = mapped_column(Boolean, default=False)


class TherapySessionModel(Base):
    __tablename__ = "therapy_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.id"))
    exercise_id: Mapped[str] = mapped_column(String, ForeignKey("therapy_exercises.id"))
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_now)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
