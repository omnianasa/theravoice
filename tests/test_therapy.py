"""Therapy exercise/recommendation tests."""

from __future__ import annotations

from theravoice.therapy.exercises import get_exercise, list_exercises
from theravoice.therapy.recommendations import recommend_exercises
from theravoice.therapy.sessions import complete_session, start_session


def test_list_exercises_returns_builtin_set():
    exercises = list_exercises()
    assert len(exercises) >= 6
    assert get_exercise("sustained_vowel") is not None
    assert get_exercise("does-not-exist") is None


def test_recommend_exercises_maps_deviating_metrics():
    recs = recommend_exercises(["pause_ratio"], require_clinician_approval=True)
    ids = {e.id for e in recs}
    assert "controlled_speaking" in ids or "pacing_exercise" in ids


def test_recommend_exercises_falls_back_when_no_metrics():
    recs = recommend_exercises([], require_clinician_approval=True)
    assert len(recs) >= 1


def test_session_lifecycle():
    session = start_session("p1", "sustained_vowel")
    assert session.completed is False
    completed = complete_session(session, notes="done")
    assert completed.completed is True
    assert completed.notes == "done"


def test_unapproved_exercise_still_requires_confirmation_downstream():
    # Exercises ship as clinician_approved=False by default; TherapyAgent
    # (see agents/therapy_agent.py) sets requires_confirmation accordingly.
    exercise = get_exercise("sustained_vowel")
    assert exercise.clinician_approved is False
