# TheraVoice Application Workflow Review

This document describes the application as it is currently implemented. It
is a product and workflow review, not a clinical evaluation or a claim that
the software is ready for clinical deployment.

## Executive Summary

TheraVoice has a connected analysis backend: transcript and audio
observations can flow through validation, biomarker extraction, personal
baseline comparison, change detection, context and agent processing,
persistence, and structured reporting.

The dashboard is not yet a complete user journey for all of those
capabilities. It supports account access, patient creation/loading,
transcript analysis, Bee sync, and review of a subset of results. Audio,
medication management, therapy sessions, and the clinician-oriented report
are API features rather than parts of the dashboard workflow. The result is
a useful working prototype with several separate entry points, not yet one
guided experience from onboarding through ongoing review.

## Application Map

| Area | Current capability | Where it is available |
|---|---|---|
| Accounts | Registration, sign-in, sign-out, bearer sessions, and account-owned patient records | Dashboard and `/auth/*` API |
| Patient records | Create and load by patient ID; set storage, audio, and LLM consent at creation | Dashboard and `/patients` API |
| Transcript observations | Submit text and run the full analysis pipeline | Dashboard, CLI, and `POST /ingestion/transcript` |
| Audio observations | Upload audio, optionally with transcript text; consent is checked | API at `POST /ingestion/audio` |
| Biomarkers and baseline | Text/acoustic metrics and rolling comparison to the same patient's history | Analysis pipeline and API; selected results in dashboard |
| Events and reports | Deviation events, daily summary, timeline, and clinical summary | API; latest biomarkers, daily summary, events, and timeline in dashboard |
| Medication | Medication records, schedules, and logged events; never changed automatically | API only |
| Therapy | Exercise catalogue, recommendations, and therapy sessions | API only |
| Bee | Mock, local sync export, or local proxy ingestion | Dashboard sync button plus CLI/API; mode is server configuration |
| LLM summaries | Optional language generation for summaries, gated by patient consent | Server configuration or patient settings in dashboard |
| AWS | Optional service adapters | Configuration/code integration, not an end-user dashboard flow |

## Current User Journey

1. A user registers or signs in. The API returns a time-limited bearer
   session; patient records created during that session are associated with
   that account.
2. The user creates a patient with an ID and display name. Data-storage
   consent is required to save observations. Audio-analysis and LLM-summary
   consent are separate choices.
3. The user loads the patient by entering the patient ID. The dashboard
   displays the latest biomarker snapshot, today's summary, recent events,
   and timeline.
4. The user submits transcript text. The backend checks the record and
   storage consent, normalizes the text, extracts available metrics,
   compares them with prior observations when enough history exists, runs
   context and agent processing, saves results, and returns a summary.
5. The user repeats observations to build a personal baseline. Development
   configuration requires five prior observations before a subsequent
   observation can be meaningfully compared; earlier responses report
   `insufficient_data`.
6. If desired, the user configures an LLM summary provider. The LLM affects
   summary wording only; it does not calculate biomarkers, detect events, or
   decide medication or therapy actions. A patient-provided key is held in
   browser memory and sent with analysis requests, not saved in the patient
   record.
7. Bee conversations can be synchronized when the server is configured for
   a real local sync export or proxy. The bundled hand-authored sample is run
   by a separate demonstration script, not loaded by the dashboard's default
   mock Bee connection.

## What Is Already Connected

- Transcript ingestion is a complete backend pipeline, not just a form that
  saves text.
- Audio ingestion reuses the baseline, detection, context, orchestration,
  and persistence stages after decoding and feature extraction.
- Biomarkers explicitly report unavailable values when their inputs are
  missing or insufficient rather than fabricating measurements.
- Baselines are patient-specific. The system does not compare people with
  population norms.
- LLM calls are optional, consent-gated, and limited to human-readable
  summaries. Provider failures fall back to deterministic wording.
- Patient access is account-scoped when requests use an account session.
- Bee sync, medications, therapy, and reports are represented by API routes
  even where the dashboard does not yet expose their full workflows.

## Advantages

- **A coherent analysis core:** ingestion, biomarker extraction, baselines,
  detection, context, agents, and persistence are coordinated behind one
  pipeline.
- **Useful without external AI:** the main analysis and deterministic
  summaries do not require an LLM provider or an API key.
- **Longitudinal framing:** comparisons use an individual's history, with
  explicit insufficient-data states while that history is being built.
- **Conservative output boundaries:** the system is descriptive and
  non-diagnostic; it does not change medication or claim that medication
  caused an observation.
- **Visible data limitations:** missing timestamps or unsuitable audio can
  make individual metrics unavailable instead of producing guessed values.
- **Consent controls:** data storage, audio analysis, and LLM processing have
  separate consent flags.
- **Multiple integration paths:** the same pipeline can be reached from the
  dashboard, CLI, API, sample Bee workflow, and optional deployment
  adapters.
- **Testable components:** the repository includes tests for the pipeline,
  API, account ownership, consent, providers, and deterministic fallbacks.

## Disadvantages and Open Workflow Issues

### High Priority: Guided Onboarding Is Missing

The dashboard introduces TheraVoice, but after sign-in the user is placed on
a large workspace page with patient ID entry and a separate create-patient
form. There is no guided first-run sequence that explains consent, creates a
record, collects the first observation, and explains what `insufficient_data`
means.

**Impact:** A first-time user may not know which action to take first or why
the first results contain no baseline comparison.

**Recommended direction:** Add a short setup flow: create/select patient,
review data-source consent, choose transcript/audio/Bee, submit the first
observation, and show baseline-building progress with the next step.

### High Priority: Patient Discovery and Profile Management Are Thin

Patients are selected by manually entering an ID. There is no account-owned
patient list, search, profile editing, or clear record-switching workflow.
The create and load areas are separate, and the same patient ID value is
used by both forms.

**Impact:** Returning users must remember identifiers, and managing more than
one patient becomes error-prone.

**Recommended direction:** Add a patient list/search and a single patient
profile view with identity, consent state, observation history, and actions.

### High Priority: Feature Access Is Split Across the Dashboard and API Docs

The dashboard does not currently provide audio upload, medication and
schedule management, medication-event logging, therapy exercise/session
flows, or the clinician-oriented report. Users must leave the dashboard for
Swagger UI or another API client to use those features.

**Impact:** The application can appear to promise a broader monitoring
workflow than a person can actually complete in the interface.

**Recommended direction:** Decide which features belong in the product's
primary user journey. Add dashboard screens for those features, or label
them clearly as developer/API capabilities until those screens exist.

### High Priority: The Sample Demonstration Is Not a Dashboard Demo

The bundled Bee sample is processed by `scripts/run_bee_demo.py`. That script
creates or uses a demo patient outside an account-owned dashboard flow. The
dashboard's default mock Bee adapter is blank, so its **Sync from Bee**
button does not automatically load the bundled sample.

**Impact:** A new user can follow the sample demo instructions but cannot
continue that same sample patient in their own signed-in dashboard.

**Recommended direction:** Provide an explicit in-dashboard demo mode that
creates sample observations under the signed-in account, labels the data as
synthetic, and lets the user follow the baseline-to-change journey without
connecting a real device.

### Medium Priority: Consent Management Is Incomplete After Creation

The create form exposes data-storage, audio-analysis, and LLM consent. The
loaded patient profile can update LLM consent, but does not provide matching
controls to review or change audio and storage consent. Consent status is
also not presented as a single patient-level summary.

**Impact:** Consent is easier to grant than to understand and manage later.

**Recommended direction:** Add a consent overview with purpose, current
state, and explicit update/revocation actions for each supported processing
type.

### Medium Priority: Baseline Progress and Follow-Up Are Not Explained

The API reports `insufficient_data` until enough history is available, but
the dashboard does not show an observation count, target, or baseline status
as a progress step. It also does not guide the person toward a next
observation or a review action.

**Impact:** Early use can feel like the system is not working, even though
it is intentionally gathering personal history.

**Recommended direction:** Show recorded observations, baseline readiness,
and an honest explanation of which metrics are not yet comparable.

### Medium Priority: LLM Configuration Can Be Confusing

The patient profile distinguishes server configuration from a provider key
entered in the browser. A patient-provided key is not persisted and must be
entered again after the browser session ends. The feature is specifically
for summary wording, not for all analysis. The app does not currently
indicate whether server-level LLM configuration is actually available.

**Impact:** Users may expect the key to be saved to their profile or expect
the LLM to influence detection and recommendations.

**Recommended direction:** Keep the non-persistence behavior explicit, show
provider readiness without exposing secrets, and continue to require
separate patient consent before sending summary evidence to an external
provider.

### Medium Priority: Review Is Read-Only and Fragmented

The dashboard shows selected latest results, but does not provide a complete
observation history, event review state, clinician summary view, or a
workflow to annotate and discuss a change. API reports exist, but are not
all represented in the dashboard.

**Impact:** It is harder to turn an observation into a useful conversation
with a care professional.

**Recommended direction:** Add a chronological observation view with clear
source, timestamp, available metrics, detected change, summary, and a
user-controlled review/notes step. Keep any clinical interpretation with a
qualified professional.

### Release Readiness: Account and Deployment Controls Need More Work

Email verification, password recovery, and login rate limiting are not
implemented. Development configuration disables API-key authentication,
and the application currently configures permissive CORS; the code comments
call for restricting origins before public exposure. Production use also
requires an intentional database, secret-management, backup, retention, and
operational-monitoring plan.

**Impact:** The current project is suitable for local evaluation and
development, not an unreviewed public deployment containing real health
information.

**Recommended direction:** Complete a security and privacy deployment review
before inviting public users or processing real patient data.

## Suggested Target Workflow

1. **Welcome and purpose:** Explain what TheraVoice observes, what it does
   not do, and that it is not a diagnosis or substitute for care.
2. **Account and patient:** Register/sign in, select or create a patient,
   and review ownership and consent in one place.
3. **Choose an observation source:** Offer transcript entry, consented audio
   upload, or configured Bee sync as visible alternatives.
4. **Confirm processing:** Show what is stored, what is sent to an optional
   provider, and which consents are needed before submission.
5. **Analyze and explain:** Return metrics, unavailable reasons, baseline
   readiness, detected changes, and a clearly labeled deterministic or
   LLM-generated summary.
6. **Review over time:** Present a longitudinal timeline and reports, with
   optional user notes or a clinician discussion prompt. Never imply
   diagnosis, causation, or medication instructions.
7. **Manage the record:** Make consent changes, data-source settings, and
   sign-out/record switching straightforward.

## Bottom Line

TheraVoice already has a strong, modular analysis foundation and a working
transcript-to-report backend. The main product gap is not a missing analysis
component; it is the orchestration of user tasks around that component. A
guided patient journey, in-dashboard access to selected API features, clear
baseline progress, and a connected sample mode would make the current
capabilities feel like one application rather than a collection of useful
parts.