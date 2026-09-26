"""Personal baseline computation.

Core principle: compare a patient primarily against their OWN historical
baseline, not population norms. If there is not enough history, we say so
explicitly (`insufficient_data`) rather than pretending a baseline exists.
"""

from __future__ import annotations

from theravoice.baseline.profile import PatientProfile
from theravoice.baseline.statistics import rolling_mean_std
from theravoice.schemas.baseline import BaselineStat, PersonalBaseline

BASELINE_STATUS_OK = "ok"
BASELINE_STATUS_INSUFFICIENT = "insufficient_data"


def compute_baseline(
    profile: PatientProfile, minimum_observations: int
) -> tuple[PersonalBaseline, dict[str, str]]:
    """Compute a PersonalBaseline from a profile's rolling histories.

    Returns:
        (baseline, status_by_metric) where status_by_metric[name] is either
        BASELINE_STATUS_OK or BASELINE_STATUS_INSUFFICIENT.
    """
    metrics: dict[str, BaselineStat] = {}
    status_by_metric: dict[str, str] = {}

    for name, history in profile.histories.items():
        values = history.values
        if len(values) < minimum_observations:
            status_by_metric[name] = BASELINE_STATUS_INSUFFICIENT
            continue
        mean, std, n = rolling_mean_std(values)
        metrics[name] = BaselineStat(mean=mean, std=std, n=n)
        status_by_metric[name] = BASELINE_STATUS_OK

    return PersonalBaseline(patient_id=profile.patient_id, metrics=metrics), status_by_metric
