"""Text-level repetition detection: repeated words and immediate repeats."""

from __future__ import annotations

import re

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower()) if text else []


def count_immediate_word_repetitions(text: str) -> int:
    """Count cases where the same word appears twice (or more) consecutively."""
    tokens = _tokenize(text)
    if len(tokens) < 2:
        return 0
    return sum(1 for a, b in zip(tokens, tokens[1:]) if a == b)


def count_repeated_phrases(text: str, phrase_length: int = 2) -> int:
    """Count consecutive repeats of short phrases (n-grams) of given length."""
    tokens = _tokenize(text)
    if len(tokens) < phrase_length * 2:
        return 0
    phrases = [
        tuple(tokens[i : i + phrase_length]) for i in range(len(tokens) - phrase_length + 1)
    ]
    return sum(1 for a, b in zip(phrases, phrases[phrase_length:]) if a == b)


def repetition_summary(text: str) -> dict[str, int]:
    return {
        "immediate_word_repetitions": count_immediate_word_repetitions(text),
        "repeated_two_word_phrases": count_repeated_phrases(text, phrase_length=2),
    }
