"""Text biomarker extraction tests."""

from __future__ import annotations

from theravoice.biomarkers.text.hesitation import count_hesitations
from theravoice.biomarkers.text.lexical_metrics import lexical_metrics
from theravoice.biomarkers.text.repetition import count_immediate_word_repetitions
from theravoice.biomarkers.text.sentence_metrics import sentence_metrics


def test_sentence_metrics_basic():
    metrics = sentence_metrics("Good morning. I am feeling okay today.")
    assert metrics["sentence_count"] == 2
    assert metrics["word_count_total"] == 7


def test_lexical_metrics_type_token_ratio():
    metrics = lexical_metrics("the cat sat on the mat")
    assert metrics["token_count"] == 6
    assert metrics["unique_token_count"] == 5


def test_hesitation_count_english():
    assert count_hesitations("um I think uh maybe") == 2


def test_hesitation_count_arabic():
    assert count_hesitations("يعني انا بخير") == 1


def test_immediate_word_repetition():
    assert count_immediate_word_repetitions("I I am fine fine today") == 2
