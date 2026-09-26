"""Biomarker repository: persistence + retrieval of biomarker values and baselines."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from theravoice.schemas.baseline import BaselineStat, PersonalBaseline
from theravoice.schemas.biomarker import BiomarkerSnapshot, BiomarkerValue
from theravoice.storage.models import BaselineStatisticModel, BiomarkerModel


class BiomarkerRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_snapshot(self, snapshot: BiomarkerSnapshot) -> None:
        for value in snapshot.values:
            model = BiomarkerModel(
                patient_id=snapshot.patient_id,
                name=value.name,
                value=value.value,
                unit=value.unit,
                confidence=value.confidence,
                source=value.source,
                available=value.available,
                reason_unavailable=value.reason_unavailable,
                timestamp=value.timestamp,
            )
            self._session.add(model)
        self._session.flush()

    def get_latest(self, patient_id: str) -> BiomarkerSnapshot | None:
        stmt = (
            select(BiomarkerModel)
            .where(BiomarkerModel.patient_id == patient_id)
            .order_by(BiomarkerModel.timestamp.desc())
            .limit(200)
        )
        models = self._session.execute(stmt).scalars().all()
        if not models:
            return None
        latest_ts = models[0].timestamp
        latest_models = [m for m in models if m.timestamp == latest_ts]
        values = [
            BiomarkerValue(
                name=m.name,
                value=m.value,
                unit=m.unit,
                confidence=m.confidence,
                timestamp=m.timestamp,
                source=m.source,
                available=m.available,
                reason_unavailable=m.reason_unavailable,
            )
            for m in latest_models
        ]
        return BiomarkerSnapshot(patient_id=patient_id, timestamp=latest_ts, values=values)

    def get_history(self, patient_id: str, metric_name: str, limit: int = 100) -> list[float]:
        stmt = (
            select(BiomarkerModel)
            .where(
                BiomarkerModel.patient_id == patient_id,
                BiomarkerModel.name == metric_name,
                BiomarkerModel.available.is_(True),
            )
            .order_by(BiomarkerModel.timestamp.asc())
            .limit(limit)
        )
        models = self._session.execute(stmt).scalars().all()
        return [float(m.value) for m in models if m.value is not None]

    def get_all(self, patient_id: str, limit: int = 500) -> list[BiomarkerValue]:
        stmt = (
            select(BiomarkerModel)
            .where(BiomarkerModel.patient_id == patient_id)
            .order_by(BiomarkerModel.timestamp.desc())
            .limit(limit)
        )
        models = self._session.execute(stmt).scalars().all()
        return [
            BiomarkerValue(
                name=m.name,
                value=m.value,
                unit=m.unit,
                confidence=m.confidence,
                timestamp=m.timestamp,
                source=m.source,
                available=m.available,
                reason_unavailable=m.reason_unavailable,
            )
            for m in models
        ]

    def save_baseline(self, baseline: PersonalBaseline) -> None:
        for metric_name, stat in baseline.metrics.items():
            model = BaselineStatisticModel(
                patient_id=baseline.patient_id,
                metric_name=metric_name,
                mean=stat.mean,
                std=stat.std,
                n=stat.n,
            )
            self._session.add(model)
        self._session.flush()

    def get_latest_baseline(self, patient_id: str) -> PersonalBaseline:
        stmt = (
            select(BaselineStatisticModel)
            .where(BaselineStatisticModel.patient_id == patient_id)
            .order_by(BaselineStatisticModel.updated_at.desc())
        )
        models = self._session.execute(stmt).scalars().all()
        metrics: dict[str, BaselineStat] = {}
        for m in models:
            if m.metric_name not in metrics:  # first (most recent) wins
                metrics[m.metric_name] = BaselineStat(mean=m.mean, std=m.std, n=m.n)
        return PersonalBaseline(patient_id=patient_id, metrics=metrics)
