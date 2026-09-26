"""Load transcripts from plain text or structured (JSON) sources."""

from __future__ import annotations

import json
from pathlib import Path


def load_transcript_text(path: str) -> str:
    """Load a plain-text transcript file, stripped of surrounding whitespace."""
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Transcript file not found: {path}")
    return file_path.read_text(encoding="utf-8").strip()


def load_transcript_json(path: str) -> dict:
    """Load a structured transcript (e.g. with timestamps) from a JSON file."""
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Transcript file not found: {path}")
    with file_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}, got {type(data).__name__}")
    return data
