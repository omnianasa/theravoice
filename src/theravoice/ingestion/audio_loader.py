"""Load audio files from disk into numpy arrays for downstream processing.

librosa/soundfile are imported lazily so that the rest of the codebase can be
imported and tested even in environments where native audio libraries are not
installed yet.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LoadedAudio:
    samples: "object"  # np.ndarray, kept untyped to avoid a hard numpy import at module load
    sample_rate: int
    duration_seconds: float


class AudioLoadError(RuntimeError):
    """Raised when an audio file cannot be read or decoded."""


def load_audio(path: str, target_sample_rate: int | None = None) -> LoadedAudio:
    """Load an audio file as mono float32 samples.

    Args:
        path: Path to a local audio file (wav/flac/ogg/mp3, whatever the
            installed libsndfile build supports).
        target_sample_rate: If given, resample to this rate.

    Raises:
        AudioLoadError: if the file cannot be loaded/decoded.
    """
    try:
        import librosa
    except ImportError as exc:  # pragma: no cover - exercised only w/o librosa installed
        raise AudioLoadError(
            "librosa is not installed; install project dependencies to enable audio loading."
        ) from exc

    try:
        samples, sample_rate = librosa.load(path, sr=target_sample_rate, mono=True)
    except Exception as exc:  # noqa: BLE001 - surface as a domain-specific error
        raise AudioLoadError(f"Failed to load audio file '{path}': {exc}") from exc

    duration_seconds = float(len(samples)) / float(sample_rate) if sample_rate else 0.0
    return LoadedAudio(samples=samples, sample_rate=sample_rate, duration_seconds=duration_seconds)
