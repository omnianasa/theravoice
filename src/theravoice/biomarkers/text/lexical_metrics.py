"""Lexical diversity metrics."""

from __future__ import annotations

import re

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    if not text:
        return []
    return _WORD_RE.findall(text.lower())


def lexical_metrics(text: str) -> dict[str, float | int]:
    tokens = tokenize(text)
    token_count = len(tokens)
    unique_count = len(set(tokens))
    type_token_ratio = (unique_count / token_count) if token_count else 0.0

    return {
        "token_count": token_count,
        "unique_token_count": unique_count,
        "type_token_ratio": type_token_ratio,
        "lexical_diversity": type_token_ratio,
    }
