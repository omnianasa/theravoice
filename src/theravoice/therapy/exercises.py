"""Built-in library of configurable, non-prescriptive speech exercises."""

from __future__ import annotations

from theravoice.schemas.therapy import Exercise

BUILT_IN_EXERCISES: list[Exercise] = [
    Exercise(
        id="sustained_vowel",
        name="Sustained Vowel",
        description="Sustain a vowel sound ('ah') for as long as comfortable.",
        duration_seconds=60,
        instructions=[
            "Take a comfortable breath.",
            "Say 'ah' and hold it steadily for as long as is comfortable.",
            "Repeat 3 times, resting between attempts.",
        ],
        clinician_approved=False,
    ),
    Exercise(
        id="articulation_drill",
        name="Articulation Drill",
        description="Practice crisp articulation with short phrases.",
        duration_seconds=120,
        instructions=[
            "Read a short list of phrases slowly and clearly.",
            "Focus on fully forming each consonant.",
        ],
        clinician_approved=False,
    ),
    Exercise(
        id="reading_aloud",
        name="Reading Aloud",
        description="Read a short passage aloud at a comfortable pace.",
        duration_seconds=180,
        instructions=["Choose a short passage.", "Read it aloud at a natural, comfortable pace."],
        clinician_approved=False,
    ),
    Exercise(
        id="controlled_speaking",
        name="Controlled Speaking",
        description="Speak in short, controlled phrases with deliberate pauses.",
        duration_seconds=120,
        instructions=["Speak in short phrases.", "Pause deliberately between phrases."],
        clinician_approved=False,
    ),
    Exercise(
        id="loudness_practice",
        name="Loudness Practice",
        description="Practice speaking slightly louder than usual, comfortably.",
        duration_seconds=90,
        instructions=["Speak a few sentences at a slightly raised, comfortable volume."],
        clinician_approved=False,
    ),
    Exercise(
        id="pacing_exercise",
        name="Pacing Exercise",
        description="Practice speaking at a deliberately even pace.",
        duration_seconds=90,
        instructions=["Speak a few sentences, aiming for an even, steady pace."],
        clinician_approved=False,
    ),
]


def get_exercise(exercise_id: str) -> Exercise | None:
    for exercise in BUILT_IN_EXERCISES:
        if exercise.id == exercise_id:
            return exercise
    return None


def list_exercises() -> list[Exercise]:
    return list(BUILT_IN_EXERCISES)
