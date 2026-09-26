"""Adherence tracking (human-logged events only; never inferred/changed by the system)."""

from __future__ import annotations

from theravoice.schemas.medication import MedicationEvent


def adherence_rate(events: list[MedicationEvent]) -> float | None:
    if not events:
        return None
    taken = sum(1 for e in events if e.status == "taken")
    return taken / len(events)
