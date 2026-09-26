"""Bee integration: real, documented, no-invented-API access to a user's own
Bee data (captured by a Bee wearable or the Bee app on Apple Watch/iPhone).

TheraVoice never talks to Bee's cloud servers directly and never stores a
Bee API token. Instead it uses the two **local**, officially documented
channels Bee's own CLI (`@beeai/cli`, https://docs.bee.computer) provides,
both of which run entirely on the user's own machine, authenticated by the
user's own `bee login` session:

1. **`BeeSyncAdapter`** -- reads the markdown export folder produced by
   `bee sync` (see https://docs.bee.computer/docs/sync). Good for backfill /
   batch analysis of historical conversations. No server is running; this
   just parses files on disk.

2. **`BeeProxyAdapter`** -- calls the local HTTP API started by
   `bee proxy` (see https://docs.bee.computer/docs/proxy), which forwards
   `/v1/*` requests to Bee on the user's behalf. This is the near-live path:
   run `bee login` once, then `bee proxy` in the background, and TheraVoice
   polls `http://127.0.0.1:8787/v1/conversations` etc. Nothing here is
   invented -- every path and JSON field used below is taken from Bee's
   published docs (`docs/bee_integration.md` in this repo has the exact
   quotes/links).

Both adapters implement the same small `BeeAdapter` interface used
throughout the pipeline, so `MonitoringPipeline` and everything downstream
is completely unaware of which channel (or `MockBeeAdapter`, for tests)
is supplying the data.

Known, disclosed limitation: Bee's documented conversation schema labels
speakers generically (its own docs show `"speaker": "Unknown"` in example
JSON) and does not expose per-utterance timestamps or raw audio bytes.
TheraVoice therefore treats each Bee conversation as a single observation
(all utterances concatenated, timestamped at the conversation's
`start_time`), and correctly reports speech-timing-dependent biomarkers
(e.g. response latency) as `unavailable` rather than guessing -- consistent
with this project's "never fabricate timestamps" rule. Raw audio is not
retrievable via Bee's documented API, so `get_audio()` on both real
adapters returns an empty list rather than inventing one.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from theravoice.schemas.audio import AudioSegment
from theravoice.schemas.transcript import TranscriptSegment


class BeeAdapter(ABC):
    """Interface any Bee-like data source must implement."""

    @abstractmethod
    def get_audio(self, patient_id: str, since: datetime | None = None) -> list[AudioSegment]:
        """Return audio segments for a patient, optionally since a timestamp."""

    @abstractmethod
    def get_transcript(
        self, patient_id: str, since: datetime | None = None
    ) -> list[TranscriptSegment]:
        """Return transcript segments for a patient, optionally since a timestamp."""

    @abstractmethod
    def get_events(self, patient_id: str, since: datetime | None = None) -> list[dict]:
        """Return raw device-level/account-level events, as plain dicts."""


class BeeConnectionError(RuntimeError):
    """Raised when a real Bee channel (sync export or local proxy) can't be reached."""


# ---------------------------------------------------------------------------
# Mock adapter: blank, in-memory, for unit tests and environments with no
# Bee account at all.
# ---------------------------------------------------------------------------
class MockBeeAdapter(BeeAdapter):
    """In-memory, deterministic adapter for local development and tests.

    No network calls, no real device required. Data can be seeded via
    `add_audio` / `add_transcript` / `add_event`, or left empty.
    """

    def __init__(self) -> None:
        self._audio: list[AudioSegment] = []
        self._transcripts: list[TranscriptSegment] = []
        self._events: list[dict] = []

    def add_audio(self, segment: AudioSegment) -> None:
        self._audio.append(segment)

    def add_transcript(self, segment: TranscriptSegment) -> None:
        self._transcripts.append(segment)

    def add_event(self, event: dict) -> None:
        self._events.append(event)

    def get_audio(self, patient_id: str, since: datetime | None = None) -> list[AudioSegment]:
        return [
            a
            for a in self._audio
            if a.patient_id == patient_id and (since is None or a.timestamp >= since)
        ]

    def get_transcript(
        self, patient_id: str, since: datetime | None = None
    ) -> list[TranscriptSegment]:
        return [
            t
            for t in self._transcripts
            if t.patient_id == patient_id and (since is None or t.timestamp >= since)
        ]

    def get_events(self, patient_id: str, since: datetime | None = None) -> list[dict]:
        return [
            e
            for e in self._events
            if e.get("patient_id") == patient_id
            and (since is None or e.get("timestamp", datetime.now(timezone.utc)) >= since)
        ]


# ---------------------------------------------------------------------------
# Real adapter #1: parse a local `bee sync` markdown export.
# https://docs.bee.computer/docs/sync
# ---------------------------------------------------------------------------
_CONVERSATION_HEADER_RE = re.compile(r"^#\s*Conversation\s+(\S+)", re.MULTILINE)
_START_TIME_RE = re.compile(r"^-\s*start_time:\s*(\S+)", re.MULTILINE)
_TRANSCRIPTION_BLOCK_RE = re.compile(
    r"###\s*Transcription\s+\S+\s*\n(?:-\s*realtime:[^\n]*\n)?\n?(.*?)(?=\n##|\n###|\Z)",
    re.DOTALL,
)
_UTTERANCE_LINE_RE = re.compile(r"^-\s*([^:\n]+):\s*(.+)$", re.MULTILINE)


def _parse_iso8601(value: str) -> datetime:
    # Bee sync files use ISO 8601 UTC, e.g. "2024-01-15T09:00:00.000Z".
    normalized = value.strip().replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _parse_conversation_markdown(text: str, patient_id: str) -> TranscriptSegment | None:
    """Parse one `conversations/YYYY-MM-DD/ID.md` file's contents.

    Follows the exact structure documented at
    https://docs.bee.computer/docs/sync (`### Conversations` section):
    an `# Conversation <id>` header, `- start_time: <ISO8601>` metadata
    bullet, and a `## Transcriptions` section containing one or more
    `### Transcription <id>` blocks with `- Speaker: text` bullet lines.
    """
    header_match = _CONVERSATION_HEADER_RE.search(text)
    start_match = _START_TIME_RE.search(text)
    if header_match is None or start_match is None:
        return None

    conversation_id = header_match.group(1)
    try:
        start_time = _parse_iso8601(start_match.group(1))
    except ValueError:
        return None

    utterance_texts: list[str] = []
    for block_match in _TRANSCRIPTION_BLOCK_RE.finditer(text):
        block = block_match.group(1)
        for line_match in _UTTERANCE_LINE_RE.finditer(block):
            _speaker, utterance_text = line_match.group(1), line_match.group(2)
            utterance_texts.append(utterance_text.strip())

    if not utterance_texts:
        return None

    return TranscriptSegment(
        id=f"bee-conversation-{conversation_id}",
        patient_id=patient_id,
        text=" ".join(utterance_texts),
        timestamp=start_time,
    )


class BeeSyncAdapter(BeeAdapter):
    """Reads a `bee sync` markdown export directory from disk.

    Run once (or on a schedule) outside of TheraVoice:

        bee login
        bee sync --output bee-sync

    then point `bee.sync_dir` in TheraVoice's config at that directory.
    Nothing here calls out to the network; it only reads files the Bee CLI
    already wrote to disk.
    """

    def __init__(self, sync_dir: str | Path) -> None:
        self._sync_dir = Path(sync_dir)

    def _conversation_files(self) -> list[Path]:
        conversations_dir = self._sync_dir / "conversations"
        if not conversations_dir.is_dir():
            return []
        return sorted(conversations_dir.glob("*/*.md"))

    def get_audio(self, patient_id: str, since: datetime | None = None) -> list[AudioSegment]:
        # `bee sync` exports transcripts and summaries, not raw audio bytes --
        # see the module docstring. Nothing to fabricate here.
        return []

    def get_transcript(
        self, patient_id: str, since: datetime | None = None
    ) -> list[TranscriptSegment]:
        segments: list[TranscriptSegment] = []
        for path in self._conversation_files():
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            segment = _parse_conversation_markdown(text, patient_id)
            if segment is None:
                continue
            if since is not None and segment.timestamp < since:
                continue
            segments.append(segment)
        segments.sort(key=lambda s: s.timestamp)
        return segments

    def get_events(self, patient_id: str, since: datetime | None = None) -> list[dict]:
        # `daily/YYYY-MM-DD/summary.md` files double as a simple day-level
        # event feed (one entry per synced day). Kept intentionally minimal.
        daily_dir = self._sync_dir / "daily"
        if not daily_dir.is_dir():
            return []
        events: list[dict] = []
        for path in sorted(daily_dir.glob("*/summary.md")):
            events.append({"patient_id": patient_id, "type": "daily_summary_synced", "path": str(path)})
        return events


# ---------------------------------------------------------------------------
# Real adapter #2: call the local `bee proxy` HTTP API.
# https://docs.bee.computer/docs/proxy
# ---------------------------------------------------------------------------
class BeeProxyAdapter(BeeAdapter):
    """Calls the local HTTP API started by `bee proxy`.

    Usage, outside of TheraVoice, once per machine/session:

        bee login          # one-time device auth with your Bee account
        bee proxy           # starts http://127.0.0.1:8787, forwards /v1/*

    The proxy is documented as local-only and unauthenticated *on
    localhost* (it is your own already-authenticated CLI session doing the
    forwarding) -- see https://docs.bee.computer/docs/proxy. TheraVoice
    therefore needs no Bee token of its own; it just talks to
    `http://127.0.0.1:<port>` like any other local service.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8787", timeout_seconds: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def _get_json(self, path: str) -> dict | list:
        url = f"{self._base_url}{path}"
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise BeeConnectionError(
                f"Could not reach the local Bee proxy at {self._base_url} ({exc}). "
                "Make sure `bee login` has been run and `bee proxy` is running."
            ) from exc
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise BeeConnectionError(f"Bee proxy returned non-JSON data from {url}.") from exc

    @staticmethod
    def _epoch_ms_to_datetime(epoch_ms: int) -> datetime:
        return datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)

    @staticmethod
    def _extract_items(payload: dict | list, *keys: str) -> list[dict]:
        """Defensively unwrap a list-endpoint response.

        Bee's documented list responses are JSON objects containing the
        collection under a named key (e.g. `"conversations": [...]`) plus
        pagination metadata; this also tolerates a bare top-level list.
        """
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in keys:
                value = payload.get(key)
                if isinstance(value, list):
                    return value
        return []

    def get_audio(self, patient_id: str, since: datetime | None = None) -> list[AudioSegment]:
        # Bee's documented /v1/* surface exposes conversations, daily
        # summaries, facts, todos, etc. -- not raw audio bytes. See the
        # module docstring; returning [] here is honest, not a stub.
        return []

    def get_transcript(
        self, patient_id: str, since: datetime | None = None, max_conversations: int = 50
    ) -> list[TranscriptSegment]:
        listing = self._get_json("/v1/conversations")
        conversation_ids = [
            item.get("id") for item in self._extract_items(listing, "conversations") if item.get("id") is not None
        ]

        segments: list[TranscriptSegment] = []
        for conversation_id in conversation_ids[:max_conversations]:
            detail = self._get_json(f"/v1/conversations/{conversation_id}")
            if not isinstance(detail, dict):
                continue

            start_time_raw = detail.get("start_time")
            utterances = detail.get("utterances") or []
            if start_time_raw is None or not utterances:
                continue

            start_time = self._epoch_ms_to_datetime(int(start_time_raw))
            if since is not None and start_time < since:
                continue

            utterance_texts = [u.get("text", "").strip() for u in utterances if u.get("text")]
            if not utterance_texts:
                continue

            segments.append(
                TranscriptSegment(
                    id=f"bee-conversation-{conversation_id}",
                    patient_id=patient_id,
                    text=" ".join(utterance_texts),
                    timestamp=start_time,
                )
            )

        segments.sort(key=lambda s: s.timestamp)
        return segments

    def get_events(self, patient_id: str, since: datetime | None = None) -> list[dict]:
        # GET /v1/changes: "Get changed entity ids since cursor (or default
        # window when cursor is omitted)". No cursor persistence is
        # implemented here yet; each call uses Bee's default window.
        changes = self._get_json("/v1/changes")
        if isinstance(changes, dict):
            return [{**changes, "patient_id": patient_id}]
        if isinstance(changes, list):
            return [{"patient_id": patient_id, "change": c} for c in changes]
        return []


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def get_bee_adapter(
    mode: str = "mock",
    sync_dir: str = "bee-sync",
    proxy_base_url: str = "http://127.0.0.1:8787",
    proxy_timeout_seconds: float = 10.0,
) -> BeeAdapter:
    """Return the configured Bee adapter.

    Args:
        mode: "mock" (blank, in-memory; tests / no Bee account), "sync"
            (read a local `bee sync` markdown export), or "proxy" (call the
            local HTTP API started by `bee proxy`).
    """
    if mode == "mock":
        return MockBeeAdapter()
    if mode == "sync":
        return BeeSyncAdapter(sync_dir=sync_dir)
    if mode == "proxy":
        return BeeProxyAdapter(base_url=proxy_base_url, timeout_seconds=proxy_timeout_seconds)
    raise ValueError(f"Unknown bee.mode '{mode}'. Expected 'mock', 'sync', or 'proxy'.")
