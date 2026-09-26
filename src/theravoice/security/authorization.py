"""Coarse-grained authorization checks (patient-scoped access).

This is a minimal placeholder: in this single-tenant local-first design,
authorization currently only checks that a patient exists and, where
relevant, that consent has been granted for the requested operation.
"""

from __future__ import annotations

from theravoice.schemas.patient import Patient


def can_analyze_audio(patient: Patient) -> bool:
    return patient.consent_audio_analysis and patient.consent_data_storage


def can_store_data(patient: Patient) -> bool:
    return patient.consent_data_storage
