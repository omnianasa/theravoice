# TheraVoice dashboard integration and deployment

The dashboard is a React/Vite single-page app. Its route definitions and request
schemas were checked against `app.openapi()` from the running FastAPI
application. The dashboard uses only the versioned `/api/v1` paths below; it
does not infer unsupported endpoints or fabricate patient/analysis data.

## Route-to-component matrix

| Frontend section | Verified API operation(s) | Required input | Expected output | Status |
|---|---|---|---|---|
| Overview | `GET /api/v1/health`, `/api/v1/info`, `/api/v1/integrations`; when a patient is selected, `GET /api/v1/patients/{patient_id}/biomarkers/latest`, `/events`, `/reports/daily` | Bearer session; patient ID for patient-specific requests | Health `{status, service}`, release/disclaimer, integration list; optional snapshot, event array, daily summary | Implemented; empty states reflect empty backend records |
| Patients | `POST /api/v1/patients`; `GET /api/v1/patients/{patient_id}` | Create: `{id, display_name, timezone?, consent_audio_analysis?, consent_data_storage?, consent_llm_processing?}`; retrieve: known patient ID | `Patient {id, display_name, timezone, consent_*, created_at}` | Implemented for create/retrieve; **listing/search is unsupported** because no list route exists |
| Speech analysis | `POST /api/v1/analyses/transcript`; `POST /api/v1/analyses/audio` | Transcript JSON `{patient_id, text}`; audio multipart fields `patient_id`, `file`, optional `text`; patient storage consent, plus audio consent for audio | `AnalysisResult {patient_id, text_length, biomarkers, baseline_status, baseline, events, actions, context, status}` | Implemented; returned values only; audio decoder formats depend on backend libraries and there is no documented upload size limit |
| Trends & timeline | `GET /api/v1/patients/{patient_id}/biomarkers`, `/events`, `/reports/timeline`, `/reports/clinical` | Bearer session and patient ID | Biomarker records (including availability, unit, timestamp and reason), events, timeline and clinical summary | Implemented as timestamp-preserving records/tables; the biomarker operation returns at most 500 records and exposes no date filter/pagination; no new chart or analytics algorithm |
| Reports & care | `GET /api/v1/patients/{patient_id}/reports/daily`; medication schedule/events GETs; therapy exercises, recommendations and sessions GETs; `POST .../therapy/sessions?exercise_id=...` | Bearer session, patient ID; exercise ID for session start | Existing report, medication, exercise and session schemas | Implemented for read workflows and starting clinician-approved exercises. Medication write operations exist but are not presented as new care-management workflows |
| Settings & integrations | `GET /api/v1/auth/me`, `POST /api/v1/auth/logout`; `PATCH /api/v1/patients/{patient_id}/consent` with `{consent_llm_processing: boolean}`; `GET /api/v1/integrations`, Bee `GET .../integrations/bee/status`, `POST .../integrations/bee/sync` | Bearer session; patient ID for consent/Bee requests | User, updated patient, backend-reported Bee configuration/status/sync result | Implemented. LLM provider and AWS status have no public status endpoint and are explicitly unavailable |

All patient-specific routes are behind `authenticate_request`; bearer-session
requests are scoped by the backend's patient ownership check. The API has no
patient enumeration route, so the dashboard only renders records returned by
an explicit known-ID lookup or successful patient creation. Do not interpret
Bee configuration as a verified live Bee connection.

The Overview's workflow monitor is a current-state aid, not an audit log or
background health probe for every operation. Account state comes from the
authentication response, patient readiness from the selected patient and
consent fields, and Bee mode from `/integrations`. It does not test Bee CLI
authentication or connectivity; in `mock` mode, a manual sync exercises the
API workflow without fetching real Bee records. Individual analysis and care
workflows report their API results in their respective sections.

## Local development

Requirements: Node.js 22.12+ with npm and a running TheraVoice API (default
`http://127.0.0.1:8000`).

```powershell
npm ci --prefix dashboard
npm run dev --prefix dashboard
```

Vite proxies `/api/v1` to `http://127.0.0.1:8000`. Set the Vite process
environment variable `THERAVOICE_API_URL` to change that development proxy
target. To use a different absolute API origin directly, copy
`dashboard/.env.example` to `dashboard/.env.local` and set
`VITE_API_BASE_URL`, for example `http://localhost:8000`. `VITE_API_BASE_URL`
is public client configuration, never a credential. The dashboard uses
`VITE_BASE_PATH=/dashboard/` for the FastAPI-mounted build; set it to `/` for
a static host serving at its root.

The app defaults to same-origin requests when `VITE_API_BASE_URL` is blank.
It constructs API requests under `/api/v1` once and rejects malformed API
origins or mixed-content HTTPS-to-HTTP API configuration.

## Production build and static hosting

```powershell
npm ci --prefix dashboard
npm --prefix dashboard test
npm run build --prefix dashboard
```

The default production base path is `/dashboard/`, matching the existing
FastAPI `StaticFiles` mount and Docker build. `npm run preview --prefix
dashboard` can preview the bundle locally. For a separately hosted static
frontend, build with `VITE_BASE_PATH=/` and set `VITE_API_BASE_URL` to the
public API origin before building. Internal navigation uses URL fragments
(`#/overview`, etc.); static hosts do not need history-route rewrites.

Deploy the generated `dashboard/dist/` directory to the selected static host.
No static-host platform was selected or configured in this repository. Serve
the bundle over HTTPS. Build-time `VITE_*` values are included in public
browser assets and must not contain API keys, LLM credentials, Bee credentials,
AWS secrets, patient records, or other sensitive data.

## Backend deployment and connectivity

Deploy the FastAPI service independently, or use the repository Dockerfile,
which builds the dashboard and serves it at `/dashboard/`. The backend must be
available at the configured API origin. If frontend and backend origins
differ, set backend `THERAVOICE_CORS_ALLOWED_ORIGINS` to the exact trusted
frontend origin(s); production CORS must not be unrestricted. HTTPS is
required in production. The API uses opaque bearer sessions (12-hour lifetime)
rather than cookie authentication; no credentialed cross-origin cookies are
needed.

Backend configuration remains server-side:

- `THERAVOICE_ENV=production` selects `config/production.yaml`.
- `THERAVOICE_DATABASE_URL` selects the database URL. Preserve its data on
  persistent storage; the default is a SQLite file and ephemeral containers
  otherwise lose records.
- `THERAVOICE_API_KEY` is an optional backend service credential. Never pass
  it to the browser; interactive dashboard users authenticate with accounts.
- `THERAVOICE_CORS_ALLOWED_ORIGINS` is a comma-separated list of exact
  allowed origins for a cross-origin frontend.
- Optional LLM provider/model/API-key variables, AWS credentials, and Bee
  source/mode configuration belong only on the backend. Patient LLM consent
  does not itself turn on an LLM; provider configuration and backend consent
  enforcement remain authoritative.

The frontend stores only the opaque bearer token in tab-scoped `sessionStorage`
so refresh can preserve the session. This is still accessible to same-origin
JavaScript and is not an XSS defense. Transcript content, uploaded audio,
patient records and analysis responses are kept in memory only and are not
written to browser storage. Cross-origin deployments should set exact CORS
origins and use HTTPS.
