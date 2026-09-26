"""Maps deviating biomarker metrics to relevant, configurable exercises.

If `require_clinician_approval` is set and an exercise is not yet approved,
it is still returned (so the app can display it) but callers must treat it as
a suggestion requiring confirmation, never an automatic clinical instruction.
"""

from __future__ import annotations

from theravoice.schemas.therapy import Exercise
from theravoice.therapy.exercises import list_exercises

_METRIC_TO_EXERCISE_IDS: dict[str, list[str]] = {
    "speech_rate_wpm": ["pacing_exercise", "controlled_speaking"],
    "articulation_rate_wpm": ["articulation_drill"],
    "pause_ratio": ["controlled_speaking", "pacing_exercise"],
    "long_pause_count": ["reading_aloud"],
    "rms_db": ["loudness_practice"],
    "pitch_coefficient_of_variation": ["sustained_vowel"],
    "f0_std_hz": ["sustained_vowel"],
    "hesitation_count": ["reading_aloud", "controlled_speaking"],
}


def recommend_exercises(
    deviating_metrics: list[str], require_clinician_approval: bool = True, max_results: int = 3
) -> list[Exercise]:
    exercises_by_id = {e.id: e for e in list_exercises()}
    seen_ids: list[str] = []

    for metric in deviating_metrics:
        for exercise_id in _METRIC_TO_EXERCISE_IDS.get(metric, []):
            if exercise_id not in seen_ids and exercise_id in exercises_by_id:
                seen_ids.append(exercise_id)

    if not seen_ids:
        seen_ids = ["reading_aloud"]

    results = [exercises_by_id[eid] for eid in seen_ids[:max_results]]

    if require_clinician_approval:
        # Exercises are still surfaced, but nothing here marks them approved
        # automatically -- `clinician_approved` stays whatever it was set to
        # by the exercise library / clinician workflow.
        return results
    return results
