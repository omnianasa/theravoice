"""BiomarkerExtractor graceful-degradation tests."""

from __future__ import annotations

from theravoice.biomarkers.extractor import BiomarkerExtractor


def test_extract_text_only():
    extractor = BiomarkerExtractor()
    snapshot = extractor.extract("p1", text="Good morning, I am feeling okay today.")
    word_count = next(v for v in snapshot.values if v.name == "word_count")
    assert word_count.available is True
    assert word_count.value == 7


def test_extract_empty_text_marks_unavailable():
    extractor = BiomarkerExtractor()
    snapshot = extractor.extract("p1", text="")
    word_count = next(v for v in snapshot.values if v.name == "word_count")
    assert word_count.available is False
    assert word_count.reason_unavailable == "empty_text"


def test_extract_no_audio_marks_speech_unavailable():
    extractor = BiomarkerExtractor()
    snapshot = extractor.extract("p1", text="hello there", samples=None, sample_rate=None)
    pause_count = next(v for v in snapshot.values if v.name == "pause_count")
    assert pause_count.available is False
    assert pause_count.reason_unavailable == "audio_unavailable"


def test_extract_never_fabricates_speech_rate_without_audio():
    extractor = BiomarkerExtractor()
    snapshot = extractor.extract("p1", text="hello there")
    speech_rate = next(v for v in snapshot.values if v.name == "speech_rate_wpm")
    assert speech_rate.available is False
