# Bee integration

TheraVoice connects to a person's **real** Bee data (captured by a Bee
wearable, or the Bee app on Apple Watch/iPhone) through Bee's own,
officially documented CLI (`@beeai/cli`) -- never through an invented or
undocumented API, and never by storing a Bee API token inside TheraVoice.

Reference: https://docs.bee.computer/docs, https://docs.bee.computer/docs/cli,
https://docs.bee.computer/docs/sync, https://docs.bee.computer/docs/proxy,
https://docs.bee.computer/docs/agentic-now.

## Two supported channels

Both run **entirely on the user's own machine**, authenticated by the
user's own `bee login` session. TheraVoice itself never talks to Bee's cloud
servers and never needs a Bee API key.

### 1. `bee.mode: sync` -- read a local export (`BeeSyncAdapter`)

Outside of TheraVoice, once (or on a schedule):

```bash
bee login                       # one-time device authentication
bee sync --output bee-sync      # exports markdown to ./bee-sync/
```

This produces `bee-sync/conversations/<date>/<id>.md` files shaped like:

```
# Conversation 123

- start_time: 2024-01-15T09:00:00.000Z
- end_time: 2024-01-15T09:30:00.000Z
- device_type: ios
- state: processed

## Transcriptions

### Transcription 456
- realtime: false

- Speaker 1: Hello, how are you?
- Speaker 2: I'm doing well, thanks!
```

Then in `config/development.yaml` (or `production.yaml`):

```yaml
bee:
  mode: sync
  sync_dir: "bee-sync"
```

`BeeSyncAdapter` (`src/theravoice/ingestion/bee.py`) parses these files
directly off disk -- no network call is made by TheraVoice at all in this
mode. Good for backfill / batch analysis of historical conversations.

### 2. `bee.mode: proxy` -- call the local HTTP API (`BeeProxyAdapter`)

Outside of TheraVoice, in a background terminal:

```bash
bee login
bee proxy                       # starts http://127.0.0.1:8787
```

`bee proxy` forwards `/v1/*` requests to Bee on the user's behalf; the docs
describe it as local-only, with your own already-authenticated CLI session
doing the forwarding. Then:

```yaml
bee:
  mode: proxy
  proxy_base_url: "http://127.0.0.1:8787"
```

`BeeProxyAdapter` calls, using only Python's standard library
(`urllib.request` -- no new dependency added):

- `GET /v1/conversations` -- list recent conversations (IDs)
- `GET /v1/conversations/:id` -- full detail: `start_time`, `end_time`,
  `utterances: [{speaker, text}, ...]`
- `GET /v1/changes` -- changed-entity feed (surfaced via `get_events`)

This is the near-live path: a "Sync from Bee" click can pick up conversations
from minutes ago.

### 3. `bee.mode: mock` (default) -- no Bee account at all

`MockBeeAdapter` is a blank, in-memory adapter you seed programmatically.
Used by the test suite and as the safe default so the project runs out of
the box with zero external dependencies.

## Known, disclosed limitations

Bee's own published JSON examples label utterance speakers generically
(`"speaker": "Unknown"`) and do not show per-utterance timestamps or a raw
audio endpoint. TheraVoice does **not** paper over this:

- Each Bee conversation becomes **one** biomarker observation (all
  utterances concatenated, timestamped at the conversation's `start_time`).
- Speech-timing-dependent biomarkers that need per-utterance timestamps
  (e.g. response latency) are correctly reported as `unavailable` for
  Bee-sourced data, never guessed.
- `get_audio()` on both real adapters returns `[]`: Bee's documented `/v1/*`
  surface and `bee sync` export raw text/summaries, not audio bytes, so
  TheraVoice never fabricates an audio segment that doesn't exist.

## Trying it without a Bee account

`data/examples/bee_sync_sample/` is a small, **hand-authored** demo export
that follows the exact `bee sync` file format above (see its own
`README.md`). Run:

```bash
python scripts/run_bee_demo.py
```

to see the full pipeline (ingestion -> biomarkers -> baseline -> detection
-> multi-agent orchestration -> persistence) run against six days of sample
conversations, ending with a deliberately more hesitant, shorter final
entry so you can see `ChangeDetector` and the agents actually produce a
`speech_pattern_change` / `text_pattern_change` event and a
`REQUEST_CHECK_IN` action once a baseline exists.

## Using your own real data

1. `bee login`
2. Either `bee sync --output bee-sync` (batch) or `bee proxy` (near-live)
3. Set `bee.mode` accordingly in `config/development.yaml`
4. `theravoice sync-bee --patient-id <your-patient-id>` (CLI), or
   `POST /patients/<your-patient-id>/bee/sync` (API / dashboard "Sync from
   Bee" button)

Either path prints/returns exactly what changed relative to that patient's
own baseline, plus any suggested check-in or exercise -- never a diagnosis.

## Apple Watch

The Bee app running on Apple Watch captures conversations through the same
Bee account as the wearable; from TheraVoice's point of view there is no
difference -- both surface through the same `bee sync` export / `bee proxy`
API described above. No Watch-specific code is needed or has been added.
