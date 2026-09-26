"""Sentence-level structural metrics."""

from __future__ import annotations

import re

_SENTENCE_SPLIT_RE = re.compile(r"[.!?\u061F\u06D4]+")
_WORD_RE = re.compile(r"\w+", re.UNICODE)


def split_sentences(text: str) -> list[str]:
    if not text:
        return []
    parts = [p.strip() for p in _SENTENCE_SPLIT_RE.split(text)]
    return [p for p in parts if p]


def sentence_metrics(text: str) -> dict[str, float | int]:
    sentences = split_sentences(text)
    sentence_count = len(sentences)
    word_counts = [len(_WORD_RE.findall(s)) for s in sentences]
    total_words = sum(word_counts)

    average_sentence_length = (total_words / sentence_count) if sentence_count else 0.0

    return {
        "sentence_count": sentence_count,
        "average_sentence_length": average_sentence_length,
        "word_count_total": total_words,
        "character_count": len(text or ""),
    }
