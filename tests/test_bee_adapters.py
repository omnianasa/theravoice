"""Tests for the Bee integration adapters.

`BeeSyncAdapter` and `BeeProxyAdapter` are exercised against locally
constructed data (a synthetic `bee sync`-shaped markdown file, and a proxy
pointed at a port nothing is listening on) so these tests need no real Bee
account, device, or network access -- exactly like the rest of the suite.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from theravoice.ingestion.bee import (
    BeeConnectionError,
    BeeProxyAdapter,
    BeeSyncAdapter,
    MockBeeAdapter,
    get_bee_adapter,
)

_SAMPLE_CONVERSATION_MD = """# Conversation 123

- start_time: 2024-01-15T09:00:00.000Z
- end_time: 2024-01-15T09:30:00.000Z
- device_type: ios
- state: processed
- created_at: 2024-01-15T09:00:00.000Z
- updated_at: 2024-01-15T10:00:00.000Z

## Short Summary

Brief description of the conversation.

## Transcriptions

### Transcription 456
- realtime: false

- Speaker 1: Good morning, how are you feeling today?
- Speaker 2: I am okay, a little tired.
"""


def _write_sync_export(tmp_path: Path) -> Path:
    conv_dir = tmp_path / "conversations" / "2024-01-15"
    conv_dir.mkdir(parents=True)
    (conv_dir / "123.md").write_text(_SAMPLE_CONVERSATION_MD, encoding="utf-8")
    return tmp_path


def test_mock_bee_adapter_filters_by_patient_and_since():
    from theravoice.schemas.transcript import TranscriptSegment

    adapter = MockBeeAdapter()
    early = TranscriptSegment(
        id="1", patient_id="p1", text="early", timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc)
    )
    late = TranscriptSegment(
        id="2", patient_id="p1", text="late", timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc)
    )
    other_patient = TranscriptSegment(
        id="3", patient_id="p2", text="other", timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc)
    )
    adapter.add_transcript(early)
    adapter.add_transcript(late)
    adapter.add_transcript(other_patient)

    result = adapter.get_transcript("p1", since=datetime(2024, 3, 1, tzinfo=timezone.utc))
    assert [s.id for s in result] == ["2"]


def test_bee_sync_adapter_parses_documented_markdown_format(tmp_path):
    export_dir = _write_sync_export(tmp_path)
    adapter = BeeSyncAdapter(sync_dir=export_dir)

    segments = adapter.get_transcript("patient-demo-001")
    assert len(segments) == 1
    segment = segments[0]
    assert segment.patient_id == "patient-demo-001"
    assert segment.timestamp == datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    assert "Good morning, how are you feeling today?" in segment.text
    assert "I am okay, a little tired." in segment.text
    # The "- realtime: false" metadata bullet must never leak into the text.
    assert "realtime" not in segment.text


def test_bee_sync_adapter_respects_since_filter(tmp_path):
    export_dir = _write_sync_export(tmp_path)
    adapter = BeeSyncAdapter(sync_dir=export_dir)

    future_cutoff = datetime(2024, 6, 1, tzinfo=timezone.utc)
    assert adapter.get_transcript("patient-demo-001", since=future_cutoff) == []


def test_bee_sync_adapter_returns_empty_audio_never_fabricated(tmp_path):
    export_dir = _write_sync_export(tmp_path)
    adapter = BeeSyncAdapter(sync_dir=export_dir)
    assert adapter.get_audio("patient-demo-001") == []


def test_bee_sync_adapter_missing_directory_returns_empty_not_error(tmp_path):
    adapter = BeeSyncAdapter(sync_dir=tmp_path / "does-not-exist")
    assert adapter.get_transcript("patient-demo-001") == []


def test_bee_proxy_adapter_raises_connection_error_when_unreachable():
    # Port 1 is a reserved/unlikely-to-be-listening port; if it does happen
    # to be open in some environment, the JSON-decode error path is also
    # wrapped in BeeConnectionError, so this stays deterministic either way.
    adapter = BeeProxyAdapter(base_url="http://127.0.0.1:1", timeout_seconds=0.5)
    with pytest.raises(BeeConnectionError):
        adapter.get_transcript("patient-demo-001")


def test_bee_proxy_adapter_never_fabricates_audio():
    adapter = BeeProxyAdapter(base_url="http://127.0.0.1:1")
    assert adapter.get_audio("patient-demo-001") == []


def test_bee_proxy_adapter_extract_items_handles_bare_list_and_named_key():
    payload_named = {"conversations": [{"id": 1}, {"id": 2}]}
    payload_bare = [{"id": 3}]
    assert BeeProxyAdapter._extract_items(payload_named, "conversations") == [{"id": 1}, {"id": 2}]
    assert BeeProxyAdapter._extract_items(payload_bare, "conversations") == [{"id": 3}]
    assert BeeProxyAdapter._extract_items({}, "conversations") == []


def test_get_bee_adapter_factory_modes(tmp_path):
    assert isinstance(get_bee_adapter(mode="mock"), MockBeeAdapter)
    assert isinstance(get_bee_adapter(mode="sync", sync_dir=str(tmp_path)), BeeSyncAdapter)
    assert isinstance(get_bee_adapter(mode="proxy"), BeeProxyAdapter)
    with pytest.raises(ValueError):
        get_bee_adapter(mode="not-a-real-mode")
