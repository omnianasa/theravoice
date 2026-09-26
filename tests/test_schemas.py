"""Schema validation tests."""

from __future__ import annotations

from theravoice.schemas.action import Action
from theravoice.schemas.baseline import BaselineStat, PersonalBaseline
from theravoice.schemas.biomarker import BiomarkerSnapshot, BiomarkerValue
from theravoice.schemas.patient import Patient


def test_patient_defaults():
    patient = Patient(id="p1", display_name="Test Patient")
    assert patient.consent_audio_analysis is False
    assert patient.timezone == "UTC"


def test_biomarker_snapshot_as_dict_excludes_unavailable():
    snapshot = BiomarkerSnapshot(
        patient_id="p1",
        values=[
            BiomarkerValue(name="a", value=1.0, source="text", available=True),
            BiomarkerValue(name="b", value=None, source="text", available=False, reason_unavailable="x"),
        ],
    )
    assert snapshot.as_dict() == {"a": 1.0}


def test_personal_baseline_metrics():
    baseline = PersonalBaseline(patient_id="p1", metrics={"a": BaselineStat(mean=1.0, std=0.5, n=5)})
    assert baseline.metrics["a"].n == 5


def test_action_type_literal():
    action = Action(patient_id="p1", type="LOG", message="test")
    assert action.type == "LOG"
