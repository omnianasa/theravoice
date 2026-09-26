"""Normalization tests."""

from __future__ import annotations

from theravoice.ingestion.normalizer import is_empty_text, normalize_text


def test_normalize_collapses_whitespace():
    assert normalize_text("hello    world\n\n") == "hello world"


def test_is_empty_text():
    assert is_empty_text("") is True
    assert is_empty_text("   ") is True
    assert is_empty_text(None) is True
    assert is_empty_text("hi") is False
