<div align="center">

  <img src="assets/owl.png" width="150" alt="TheraVoice Owl">

  <h1>TheraVoice</h1>

  <p>
    <strong>Open-source, non-diagnostic speech and communication monitoring</strong>
  </p>

  <br>

</div>


TheraVoice helps people and care teams observe how speech and language
patterns change over time. It compares each observation with that person's
own history, then presents descriptive signals, summaries, and optional
check-in suggestions. Parkinson's disease is a motivating use case; the
architecture is disease-agnostic.

TheraVoice is an assistive software project, not a medical device or a
replacement for clinical assessment. It does not diagnose conditions or
recommend medication changes. Review [Limitations and safety](docs/limitations.md)
before using it with real health information.

---

## Table of contents

- [What you can try](#what-you-can-try)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [Hands-on feature tour](#hands-on-feature-tour)
- [Configuration](#configuration)
- [Accounts](#accounts)
- [LLM integration](#llm-integration)
- [API](#api)
- [Biomarker system](#biomarker-system)
- [Baseline system](#baseline-system)
- [Multi-agent architecture](#multi-agent-architecture)
- [Dashboard](#dashboard)
- [Privacy](#privacy)
- [Bee integration](#bee-integration)
- [AWS adapter](#aws-adapter)
- [Testing](#testing)
- [Examples](#examples)
- [Documentation](#documentation)
- [Safety and limitations](#safety-and-limitations)
- [Contributing](#contributing)
- [License](#license)

## What you can try

- A FastAPI service with interactive OpenAPI documentation.
- A React dashboard for account sign-in, patient records, transcript
  analysis, biomarkers, daily summaries, events, and timelines.
- Text and audio analysis, with unavailable metrics explicitly identified
  rather than guessed.
- Personal baselines and change detection that need no external AI service.
- Optional medication schedules, therapy exercises, and session tracking.
- A bundled Bee-format sample that demonstrates a multi-day monitoring
  workflow without a Bee device or account.
- Optional OpenAI or Gemini summary generation, gated by patient consent.
- Optional AWS adapters, disabled by default.

## Architecture


Every stage is a separate, independently-replaceable module under
`src/theravoice/`. The full request/response flow for
`POST /ingestion/transcript` is implemented end-to-end in
`pipeline/analysis_pipeline.py`:

```
receive transcript → validate patient → normalize → extract biomarkers
  → load/compute personal baseline → run change detection
  → run context engine → run multi-agent orchestrator
  → persist biomarkers/events/actions → return structured result
```

## Quick start

Requirements: Python 3.12 or newer and Node.js with npm to build the
dashboard. Run commands from the repository root. The PowerShell commands
below are suitable for Windows; equivalent POSIX commands follow.

### Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
npm ci --prefix dashboard
npm run build --prefix dashboard
.\.venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
npm ci --prefix dashboard
npm run build --prefix dashboard
```

Start the development API:

```powershell
$env:THERAVOICE_ENV = "development"
theravoice serve --reload
```

On macOS/Linux, use `THERAVOICE_ENV=development theravoice serve --reload`.
The first startup initializes the configured database. Open the dashboard at
http://127.0.0.1:8000/dashboard/ or the API explorer at
http://127.0.0.1:8000/docs. Development defaults to SQLite, the mock Bee
adapter, deterministic summaries, and API-key authentication disabled. The
dashboard still uses account sign-in and scopes patient records to their
owning account.

To run the containerized application instead, use Docker Compose:

```bash
docker compose up --build
```

The image builds the dashboard and runs the API with the production
configuration. Register or sign in through the dashboard; production API
requests require an account bearer token or a configured service API key.

## Hands-on feature tour

### 1. Create an account and patient

Open `/dashboard/`, choose **Sign up**, and create an account. Create a
patient record with a unique ID such as `patient-demo-001`. Grant data-storage
consent to save observations. For the optional audio and LLM exercises below,
also grant their separate consent flags. Use synthetic or sample data for
this walkthrough, not real patient information.

### 2. Analyze speech and build a personal baseline

Use **Analyze a transcript** in the dashboard, or run the CLI after creating
the demo patient in the local database:

```powershell
python scripts/seed_demo_patient.py
theravoice analyze --patient-id patient-demo-001 --text "Good morning, I am feeling okay today."
```

On Windows, activate `.venv` first or invoke the executables under
`.venv\Scripts`. Submit several distinct observations for the same patient.
The default development baseline requires
five observations; earlier results correctly report `insufficient_data`.
After analysis, explore the latest biomarkers, daily summary, events, and
timeline in the dashboard. The complete response is also returned by the
CLI and `POST /ingestion/transcript`.

### 3. Try audio, medication, and therapy endpoints

The dashboard focuses on patient creation, transcript analysis, Bee sync,
and reviewing monitoring results. Use Swagger UI at `/docs` for the broader
API: upload audio at `POST /ingestion/audio` (the patient must have audio
consent), inspect or update medication schedules and adherence records, list
therapy exercises and recommendations, and create/list therapy sessions.
The API explorer shows each request schema and response. Audio is analyzed
in memory by default and raw audio is not retained.

### 4. Run the bundled Bee demonstration

In a second terminal, run the sample export through the full monitoring
pipeline:

```powershell
python scripts/run_bee_demo.py
```

This uses six hand-authored Bee-format sample conversations, requires no
Bee account, and demonstrates baseline-building followed by a changed
observation. It is incremental: subsequent runs report no new conversations
after the fixture has been processed. The fixture's provenance and format
are described in
[`data/examples/bee_sync_sample/README.md`](data/examples/bee_sync_sample/README.md).

To connect your own Bee data, follow
[`docs/bee_integration.md`](docs/bee_integration.md); the project supports a
local `bee sync` export and Bee's local proxy.

### 5. Enable optional LLM summaries

LLM generation is off by default and only affects the human-readable daily
summary. Set a provider key in the process environment and enable
`consent_llm_processing` on the patient before testing. For example, in
PowerShell:

```powershell
$env:THERAVOICE_LLM_PROVIDER = "openai"
$env:THERAVOICE_LLM_MODEL = "gpt-4o-mini"
$env:THERAVOICE_LLM_API_KEY = "<provider-api-key>"
theravoice serve --reload
```

Use `gemini` to select Google Gemini. Do not commit or paste a real key into
source control. Only structured summary evidence is sent to the provider;
it can still contain sensitive health information. Read
[`docs/llm_integration.md`](docs/llm_integration.md) before enabling an
external provider.

### 6. Try the API or run the tests

The transcript endpoint can also be called directly:

```bash
curl -X POST http://127.0.0.1:8000/ingestion/transcript \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"patient-demo-001","text":"Good morning, I am feeling okay today."}'
```

To run the complete test suite from the repository root:

```bash
python -m pytest -q
```

On Windows, if the environment is not activated, run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Configuration

Configuration is YAML-first, selected by `THERAVOICE_ENV`
(`development` | `testing` | `production`), under `config/`. A small,
explicit set of environment variables can override sensitive values without
touching YAML or source control. See the YAML examples under [`config/`](config/)
and use environment variables or a secret manager for sensitive values:

| Env var | Overrides |
|---|---|
| `THERAVOICE_ENV` | which YAML file is loaded |
| `THERAVOICE_DATABASE_URL` | `database.url` |
| `THERAVOICE_API_KEY` | `security.api_key` (also sets `require_api_key: true`) |
| `THERAVOICE_LLM_PROVIDER` | `llm.provider` (`none`, `openai`, or `gemini`) |
| `THERAVOICE_LLM_MODEL` | `llm.model` (provider default when empty) |
| `THERAVOICE_LLM_API_KEY` | `llm.api_key` (keep this secret out of YAML and source control) |
| `THERAVOICE_LLM_TIMEOUT_SECONDS` | `llm.timeout_seconds` |
| `THERAVOICE_AWS_ENABLED` | `aws.enabled` |
| `AWS_REGION` | `aws.region` |

Key config sections: `database`, `security`, `privacy`, `baseline`,
`detection`, `hesitation` (per-language markers), `therapy`, `llm`, `aws`,
`bee`, `logging`. Configuration examples live in [`config/`](config/);
there is no checked-in `.env` file. Set secrets in the process environment
or a secret manager. LLM setup and provider behavior are documented in
[`docs/llm_integration.md`](docs/llm_integration.md).

When `security.require_api_key` is enabled, protected API routes, including
`/health`, require either the configured service key in `X-API-Key` or a
valid account bearer token. The production configuration enables this and
fails closed for requests without either credential. Development defaults
to authentication disabled; do not expose that configuration to an
untrusted network. Set `THERAVOICE_API_KEY` through a secret manager or
environment variable before deployment.

## Accounts

Anyone can register with `POST /auth/register` using an email, display name,
and password of at least 12 characters. `POST /auth/login` returns a bearer
token that expires after 12 hours; send it as
`Authorization: Bearer <access_token>`. Use `POST /auth/logout` to revoke the
current session. Passwords are stored as scrypt hashes, and session tokens
are stored only as hashes.

Patients created with an account session belong to that account. Other
accounts receive `404` when requesting those patients or submitting
observations for them. Existing patient rows are not automatically assigned
to an account, so migrate ownership before account users need those records.
Email verification, password recovery, and login rate limiting are not yet
implemented; use HTTPS and add those controls before a public production
launch.

## LLM Integration

The current LLM integration adds optional natural-language generation to the
daily summary while keeping TheraVoice's structured analysis deterministic:

- A provider-neutral client supports OpenAI Chat Completions and Google
  Gemini `generateContent`, using Python's standard library rather than a new
  runtime SDK dependency.
- Provider and model selection, API key, and positive request timeout come
  from YAML settings with environment-variable overrides. The provider is
  `none` by default, so existing installations continue to use deterministic
  summaries without credentials or network access.
- Only `SummaryAgent` uses the LLM. Biomarker extraction, event detection,
  medication handling, and therapy recommendations remain functional and
  deterministic.
- A summary request requires the patient's separate
  `consent_llm_processing` flag, which defaults to `false`. It can be set at
  patient creation or changed/revoked with
  `PATCH /patients/{patient_id}/consent`.
- Only structured evidence descriptions, context notes, and suggested-action
  messages are sent for generation. Patient IDs and raw transcripts are not
  included. These fields may still contain sensitive health information.
- Provider timeouts, network/HTTP errors, missing credentials, and unknown
  providers fall back to the deterministic summary. The application's
  non-diagnostic disclaimer is retained. Generated text never determines
  events, medication actions, or therapy recommendations.
- The ingestion response reports the summary outcome in
  `context.summary_generation_status`: `generated`, `fallback`, or
  `deterministic`. A provider failure also sets
  `context.summary_generation_error` to `provider_failure`; raw provider
  errors stay in server logs.
- Provider calls currently use synchronous HTTP clients. The configured
  timeout bounds each call but does not free the request worker while it
  waits. Async clients, concurrency limits, and provider-specific
  retry/rate-limit handling are not implemented.
- Existing databases gain the new consent column during startup, with
  existing patients defaulted to no LLM consent.

The provider-specific configuration and data-handling guidance is in
[`docs/llm_integration.md`](docs/llm_integration.md).

## API

| Method & Path | Purpose |
|---|---|
| `GET /health` | Liveness check |
| `POST /patients` | Create a patient (consent flags default to false) |
| `GET /patients/{id}` | Fetch a patient |
| `PATCH /patients/{id}/consent` | Update/revoke LLM-processing consent |
| `POST /ingestion/transcript` | **Runs the full analysis pipeline** on a transcript |
| `POST /ingestion/audio` | Loads/validates an audio upload (see note below) |
| `GET /patients/{id}/biomarkers` | All persisted biomarker values |
| `GET /patients/{id}/biomarkers/latest` | Most recent biomarker snapshot |
| `GET /patients/{id}/events` | Detected deviation events |
| `POST/GET /patients/{id}/medications...` | Medication + schedule + adherence (never auto-changed) |
| `GET/POST /patients/{id}/therapy/...` | Exercises, recommendations, sessions |
| `GET /patients/{id}/reports/daily` | Daily summary |
| `GET /patients/{id}/reports/timeline` | Chronological event timeline |
| `GET /patients/{id}/reports/clinical` | Clinician-oriented longitudinal summary |
| `POST /patients/{id}/bee/sync` | Pull new conversations from the configured Bee channel and analyze them |

`POST /ingestion/transcript` example:

```bash
curl -X POST http://127.0.0.1:8000/ingestion/transcript \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "patient-demo-001", "text": "Good morning, I am feeling okay today."}'
```

Response shape:

```json
{
  "patient_id": "patient-demo-001",
  "text_length": 39,
  "biomarkers": { "word_count": 7.0, "hesitation_count": 0.0, "...": "..." },
  "baseline_status": "insufficient_data",
  "baseline": {},
  "events": [],
  "actions": [],
  "context": { "notes": [], "summary_text": "" },
  "status": "processed"
}
```

> **Note on `POST /ingestion/audio`**: fully wired end-to-end via
> `AnalysisPipeline.run_audio()` — it validates consent, decodes the upload
> (via `librosa`), extracts acoustic biomarkers (and text biomarkers too, if
> an optional accompanying `text` form field is provided — e.g. from ASR),
> then runs the same baseline → detection → context → orchestrator →
> persistence flow as `/ingestion/transcript`. Word-count-dependent metrics
> (speech rate, articulation rate) are only computed when `text` is
> supplied; otherwise they're correctly marked `unavailable` rather than
> fabricated.

## Biomarker system

`biomarkers/extractor.py` (`BiomarkerExtractor`) is the single entry point.
It **never fabricates values** — every `BiomarkerValue` carries an
`available` flag and, when `false`, a `reason_unavailable`
(`empty_text`, `audio_unavailable`, `audio_too_short`,
`word_count_unavailable`, ...).

- **Text** (`biomarkers/text/`): hesitation (configurable EN/AR markers),
  repetition, response latency (requires real timestamps or returns
  unavailable), sentence metrics, lexical diversity.
- **Speech/acoustic** (`biomarkers/speech/`): speech rate, articulation
  rate, pauses, pitch (F0 via `librosa.pyin`), intensity (RMS dB), voice
  quality (ZCR, spectral centroid/bandwidth — explicitly descriptive, not
  clinical-grade), monotonicity (pitch coefficient of variation).

## Baseline system

`baseline/` implements a rolling personal baseline per metric
(`baseline.rolling_window_size` observations), computed only once
`baseline.minimum_observations` have been recorded. Below that threshold,
`baseline_status = "insufficient_data"` is returned explicitly rather than
comparing against a fabricated or population baseline.

## Multi-agent architecture

`agents/orchestrator.py` runs, in order: `SpeechAgent` → `TextAgent` →
`ContextAgent` → `MedicationAgent` → `TherapyAgent` → `SummaryAgent`, all
communicating via the Pydantic `AgentRequest`/`AgentResponse` schemas
(`schemas/agent.py`). Events are only created from real evidence — no agent
fabricates an event to "demonstrate" functionality.

Which agents run at all is controlled by the top-level **`agents/manifest.yaml`**
(operator-facing config, separate from the code in `src/theravoice/agents/`):
set an agent's `enabled: false` there to skip it entirely, with no code
change or redeploy — `AgentOrchestrator` reads it via `agents/manifest.py`
and fails open (every agent defaults to enabled) if the file is missing or
malformed.

## Dashboard

`dashboard/` is a React single-page app served by FastAPI at `/dashboard/`
when its production bundle exists. Build it with `npm ci --prefix dashboard`
and `npm run build --prefix dashboard` before starting the API. The dashboard
supports account sign-in, patient creation, transcript analysis, Bee sync,
and review of biomarkers, daily summaries, events, and timelines. For local
Vite development, run `npm run dev --prefix dashboard` and set
`VITE_API_BASE` if the API is hosted at a non-default address; the `api`
query parameter can also override the API URL.

## Privacy

`security/privacy.py` enforces `privacy.require_data_storage_consent` and
`privacy.require_audio_consent` before storing data or analyzing audio.
`privacy.store_raw_audio: false` (the default) means audio is analyzed
in-memory and never persisted to disk/DB. `security/audit.py` logs sensitive
operations (never secrets, never raw audio/transcript content).

## Bee integration

TheraVoice connects to **real** Bee data (a Bee wearable, or the Bee app on
Apple Watch/iPhone) through Bee's own documented CLI -- never an invented
API, never a stored Bee token. Two real, local channels are supported,
selected via `bee.mode` in config:

- **`sync`** -- `BeeSyncAdapter` reads a local `bee sync` markdown export
  from disk.
- **`proxy`** -- `BeeProxyAdapter` calls the local HTTP API started by
  `bee proxy` (`GET /v1/conversations`, `/v1/conversations/:id`,
  `/v1/changes`), using only the standard library (`urllib`) -- no new
  dependency.
- **`mock`** (default) -- blank, in-memory `MockBeeAdapter`, no Bee account
  needed.

See **[`docs/bee_integration.md`](docs/bee_integration.md)** for exact
commands, cited documentation links, and disclosed limitations (e.g. Bee's
documented schema doesn't expose per-utterance timestamps or raw audio, so
TheraVoice correctly reports those as `unavailable` rather than guessing).

**Try it now, no Bee account needed:**

```bash
python scripts/run_bee_demo.py
```

This runs the full pipeline against `data/examples/bee_sync_sample/` (a
small, clearly-labeled hand-authored demo export in the exact `bee sync`
format) and prints what changed and what the system suggests.

**With your own real data:**

```bash
bee login
bee sync --output bee-sync        # or: bee proxy  (see docs/bee_integration.md)
theravoice sync-bee --patient-id patient-demo-001
```

or via the API / dashboard's "Sync from Bee" button:
`POST /patients/{id}/bee/sync`.

## AWS adapter

`aws/` provides optional S3, DynamoDB, Bedrock, Lambda, and SNS adapters,
all guarded behind `aws.enabled: true` and a lazy `boto3` import — the
system runs fully without AWS or the `aws` extra installed.

Install the optional dependency with one of these commands:

```bash
python -m pip install -e ".[aws]"
# Or include it with the development dependencies:
python -m pip install -e ".[dev,aws]"
```

Configure AWS credentials through the standard AWS credential chain, set
`THERAVOICE_AWS_ENABLED=true`, and provide the resource settings required by
the adapter you use.

> Note: `aws/lambda.py` is named to match the target project structure;
> since `lambda` is a reserved Python keyword, import it via
> `importlib.import_module("theravoice.aws.lambda")` rather than a normal
> `import` statement.

## Testing

```bash
python -m pytest -q
```

Test modules cover schemas, normalization, text/speech biomarkers, the
`BiomarkerExtractor`'s graceful-degradation behavior, baseline
(`insufficient_data` and update behavior), z-score change detection,
context/medication rules (including "never claims causation"), agents and
the orchestrator (including "medication agent never emits a medication
change"), repositories, the full FastAPI surface, and the end-to-end
`AnalysisPipeline`. The LLM tests cover provider request formatting,
configuration, timeout handling, consent enforcement, deterministic
fallback, and the existing-database consent-column upgrade.

Expected output: all tests pass (`pytest` exits 0). Tests run against an
isolated temp-file SQLite database per session (see `tests/conftest.py`) and
use `THERAVOICE_ENV=testing`, which lowers `baseline.minimum_observations`
to 3 for faster baseline-building test scenarios.

## Examples

- `examples/analyze_transcript_example.py` — run the pipeline directly, no
  HTTP layer.
- `scripts/seed_demo_patient.py` — seed `patient-demo-001`.
- `data/schemas/sample_patient.json` — an example `Patient` payload.
- `data/examples/sample_transcripts/sample_01.txt` — the canonical example
  transcript from the spec ("Good morning, I am feeling okay today.").

## Documentation

- [Limitations and non-diagnostic scope](docs/limitations.md): intended use,
  data integrity, medication and therapy boundaries, and safety.
- [LLM integration](docs/llm_integration.md): provider setup, consent, data
  handling, and fallback behavior.
- [Bee integration](docs/bee_integration.md): local sync and proxy setup,
  sample data, and known data limitations.
- [Sample Bee export](data/examples/bee_sync_sample/README.md): fixture
  provenance and how the bundled conversations demonstrate change detection.
- [Development and deployment configuration](config/): development,
  testing, and production YAML settings.

The interactive API reference is available at `/docs` while the service is
running; the OpenAPI schema is at `/openapi.json`.

## Safety and limitations

See [`docs/limitations.md`](docs/limitations.md) — this project is
deliberately non-diagnostic and non-prescriptive. Do not use it as a
diagnostic tool, treatment recommendation, or substitute for clinical care.

## Contributing

Issues, documentation improvements, and pull requests are welcome. Before
opening a pull request, run the test suite and linter from the repository
root:

```bash
python -m pytest -q
ruff check .
```

## License

MIT — see [`LICENSE`](LICENSE).
