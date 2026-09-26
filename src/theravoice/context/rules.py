"""Simple, explicit rules combining contextual signals.

Rules here produce *contextual observations*, never causal medical claims.
"""

from __future__ import annotations

from theravoice.context.medication import MedicationProximity


def describe_medication_proximity(proximities: list[MedicationProximity]) -> list[str]:
    notes: list[str] = []
    for p in proximities:
        if p.within_window:
            notes.append(
                f"Observation occurred near a scheduled medication window "
                f"(medication_id={p.medication_id}, scheduled_time={p.scheduled_time})."
            )
    return notes
