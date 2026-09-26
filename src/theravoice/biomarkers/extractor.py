"""Central biomarker extraction interface.

`BiomarkerExtractor` is the single entry point downstream code (the analysis
pipeline, agents) should use. It always returns a `BiomarkerSnapshot`, and it
never fabricates values: metrics that cannot be computed (missing audio,
missing timestamps, empty text, audio too short, malformed input) are marked
`available=False` with a `reason_unavailable`, rather than omitted silently
or invented.
"""

from __future__ import annotations

from datetime import datetime, timezone

from theravoice.biomarkers.speech.articulation_rate import articulation_rate_wpm
from theravoice.biomarkers.speech.hesitation import long_pause_count
from theravoice.biomarkers.speech.intensity import intensity_metrics
from theravoice.biomarkers.speech.monotonicity import monotonicity_metrics
from theravoice.biomarkers.speech.pauses import pause_metrics
from theravoice.biomarkers.speech.pitch import pitch_metrics
from theravoice.biomarkers.speech.speech_rate import speech_rate_wpm
from theravoice.biomarkers.speech.voice_quality import voice_quality_metrics
from theravoice.biomarkers.text.hesitation import count_hesitations
from theravoice.biomarkers.text.lexical_metrics import lexical_metrics
from theravoice.biomarkers.text.repetition import repetition_summary
from theravoice.biomarkers.text.sentence_metrics import sentence_metrics
from theravoice.ingestion.normalizer import is_empty_text, normalize_text
from theravoice.preprocessing.silence import detect_silence_intervals
from theravoice.schemas.biomarker import BiomarkerSnapshot, BiomarkerValue


def _value(
    name: str,
    value: float | None,
    unit: str | None,
    source: str,
    reason_unavailable: str | None = None,
) -> BiomarkerValue:
    available = value is not None
    return BiomarkerValue(
        name=name,
        value=value,
        unit=unit,
        source=source,
        available=available,
        reason_unavailable=None if available else (reason_unavailable or "value_unavailable"),
    )


class BiomarkerExtractor:
    """Extracts speech and text biomarkers into a unified snapshot."""

    def __init__(self, hesitation_markers: list[str] | None = None) -> None:
        self._hesitation_markers = hesitation_markers

    # ---- text ---------------------------------------------------------
    def extract_text(self, patient_id: str, text: str) -> list[BiomarkerValue]:
        """Extract descriptive text/language biomarkers. Never fabricates timing."""
        values: list[BiomarkerValue] = []

        if is_empty_text(text):
            return [
                _value("word_count", None, "words", "text", "empty_text"),
                _value("sentence_count", None, "sentences", "text", "empty_text"),
                _value("lexical_diversity", None, None, "text", "empty_text"),
                _value("hesitation_count", None, "count", "text", "empty_text"),
                _value("repetition_count", None, "count", "text", "empty_text"),
            ]

        normalized = normalize_text(text)
        sm = sentence_metrics(normalized)
        lm = lexical_metrics(normalized)
        rep = repetition_summary(normalized)
        hesitations = count_hesitations(normalized, self._hesitation_markers)

        values.append(_value("word_count", float(sm["word_count_total"]), "words", "text"))
        values.append(_value("sentence_count", float(sm["sentence_count"]), "sentences", "text"))
        values.append(
            _value(
                "average_sentence_length",
                float(sm["average_sentence_length"]),
                "words_per_sentence",
                "text",
            )
        )
        values.append(_value("character_count", float(sm["character_count"]), "characters", "text"))
        values.append(_value("token_count", float(lm["token_count"]), "tokens", "text"))
        values.append(
            _value("unique_token_count", float(lm["unique_token_count"]), "tokens", "text")
        )
        values.append(_value("lexical_diversity", float(lm["type_token_ratio"]), None, "text"))
        values.append(_value("hesitation_count", float(hesitations), "count", "text"))
        values.append(
            _value(
                "immediate_word_repetitions",
                float(rep["immediate_word_repetitions"]),
                "count",
                "text",
            )
        )
        values.append(
            _value(
                "repeated_two_word_phrases",
                float(rep["repeated_two_word_phrases"]),
                "count",
                "text",
            )
        )
        # Response latency and text-based speech rate require timestamps we
        # do not fabricate here; the caller (pipeline) supplies them if known.
        return values

    # ---- speech (audio) -------------------------------------------------
    def extract_speech(
        self,
        patient_id: str,
        samples: "object | None",
        sample_rate: int | None,
        word_count: int | None = None,
    ) -> list[BiomarkerValue]:
        """Extract descriptive acoustic biomarkers from audio, if available."""
        if samples is None or sample_rate is None:
            reason = "audio_unavailable"
            names_units = [
                ("pause_count", "count"),
                ("pause_ratio", None),
                ("mean_pause_duration_seconds", "seconds"),
                ("max_pause_duration_seconds", "seconds"),
                ("f0_mean_hz", "Hz"),
                ("f0_std_hz", "Hz"),
                ("pitch_coefficient_of_variation", None),
                ("rms_db", "dB"),
                ("zero_crossing_rate", None),
                ("spectral_centroid_hz", "Hz"),
                ("articulation_rate_wpm", "words_per_minute"),
                ("speech_rate_wpm", "words_per_minute"),
            ]
            return [_value(n, None, u, "speech", reason) for n, u in names_units]

        import numpy as np  # local import: only needed when audio is present

        samples_arr = np.asarray(samples, dtype=np.float32)
        total_duration = float(len(samples_arr)) / float(sample_rate) if sample_rate else 0.0

        if total_duration < 0.2:
            reason = "audio_too_short"
            names_units = [
                ("pause_count", "count"),
                ("pause_ratio", None),
                ("mean_pause_duration_seconds", "seconds"),
                ("max_pause_duration_seconds", "seconds"),
                ("f0_mean_hz", "Hz"),
                ("f0_std_hz", "Hz"),
                ("pitch_coefficient_of_variation", None),
                ("rms_db", "dB"),
                ("zero_crossing_rate", None),
                ("spectral_centroid_hz", "Hz"),
                ("articulation_rate_wpm", "words_per_minute"),
                ("speech_rate_wpm", "words_per_minute"),
            ]
            return [_value(n, None, u, "speech", reason) for n, u in names_units]

        silences = detect_silence_intervals(samples_arr, sample_rate)
        pm = pause_metrics(silences, total_duration)
        pitch = pitch_metrics(samples_arr, sample_rate)
        mono = monotonicity_metrics(pitch["f0_mean_hz"], pitch["f0_std_hz"], pitch["f0_range_hz"])
        intensity = intensity_metrics(samples_arr)
        vq = voice_quality_metrics(samples_arr, sample_rate)
        long_pauses = long_pause_count(silences)

        values = [
            _value("pause_count", float(pm["pause_count"]), "count", "speech"),
            _value("pause_ratio", float(pm["pause_ratio"]), None, "speech"),
            _value(
                "mean_pause_duration_seconds",
                float(pm["mean_pause_duration_seconds"]),
                "seconds",
                "speech",
            ),
            _value(
                "max_pause_duration_seconds",
                float(pm["max_pause_duration_seconds"]),
                "seconds",
                "speech",
            ),
            _value("long_pause_count", float(long_pauses), "count", "speech"),
            _value("f0_mean_hz", pitch["f0_mean_hz"], "Hz", "speech"),
            _value("f0_std_hz", pitch["f0_std_hz"], "Hz", "speech"),
            _value(
                "pitch_coefficient_of_variation",
                mono["pitch_coefficient_of_variation"],
                None,
                "speech",
            ),
            _value("rms_db", intensity["rms_db"], "dB", "speech"),
            _value("zero_crossing_rate", vq["zero_crossing_rate"], None, "speech"),
            _value("spectral_centroid_hz", vq["spectral_centroid_hz"], "Hz", "speech"),
        ]

        if word_count is not None:
            values.append(
                _value(
                    "speech_rate_wpm",
                    speech_rate_wpm(word_count, total_duration),
                    "words_per_minute",
                    "speech",
                )
            )
            values.append(
                _value(
                    "articulation_rate_wpm",
                    articulation_rate_wpm(
                        word_count, total_duration, pm["total_pause_duration_seconds"]
                    ),
                    "words_per_minute",
                    "speech",
                )
            )
        else:
            values.append(
                _value("speech_rate_wpm", None, "words_per_minute", "speech", "word_count_unavailable")
            )
            values.append(
                _value(
                    "articulation_rate_wpm",
                    None,
                    "words_per_minute",
                    "speech",
                    "word_count_unavailable",
                )
            )

        return values

    # ---- combined ---------------------------------------------------------
    def extract(
        self,
        patient_id: str,
        text: str | None = None,
        samples: "object | None" = None,
        sample_rate: int | None = None,
    ) -> BiomarkerSnapshot:
        """Extract all available biomarkers and return a unified snapshot."""
        values: list[BiomarkerValue] = []

        text_word_count: int | None = None
        if text is not None:
            text_values = self.extract_text(patient_id, text)
            values.extend(text_values)
            for v in text_values:
                if v.name == "word_count" and v.available:
                    text_word_count = int(v.value)

        speech_values = self.extract_speech(
            patient_id, samples, sample_rate, word_count=text_word_count
        )
        values.extend(speech_values)

        return BiomarkerSnapshot(
            patient_id=patient_id,
            timestamp=datetime.now(timezone.utc),
            values=values,
        )
