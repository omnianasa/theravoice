# Limitations and Non-Diagnostic Nature

TheraVoice is an **assistive, descriptive monitoring tool**. It is explicitly
**not**:

- a diagnostic device or software-as-a-medical-device product,
- a system that can diagnose Parkinson's disease or any other condition,
- a system that can conclude a biomarker "proves" disease progression,
- a system that prescribes, changes, or infers the effect of medication,
- a replacement for clinical judgement or periodic clinical follow-up.

## What it actually does

TheraVoice extracts descriptive, longitudinal speech and language metrics
(e.g. pause ratio, lexical diversity, hesitation counts, pitch variation),
compares each metric **only against that same patient's own historical
values**, and reports statistically-described deviations (`normal`,
`warning`, `significant`, `insufficient_data`) — never a diagnosis, never a
population-normed clinical score.

## Data integrity

- Biomarkers are never fabricated. If audio is missing, too short, or
  transcript timestamps are unavailable, the affected metric is marked
  `available: false` with a `reason_unavailable`, rather than guessed at.
- Baselines require a configurable minimum number of prior observations
  (`baseline.minimum_observations`) before any comparison is made. Until
  then, the system explicitly reports `insufficient_data`.
- Acoustic "voice quality" features (zero-crossing rate, spectral centroid,
  spectral bandwidth) are general-purpose signal-processing descriptors, not
  clinically validated measurements such as calibrated jitter/shimmer/HNR.

## Medication

- The system never changes a medication schedule or dosage.
- It may note that an observation occurred near a scheduled medication
  window (a purely temporal fact) but never claims medication caused a
  change or "wore off".
- All medication-related outputs are framed as reminders or check-in
  suggestions (`REQUEST_CHECK_IN`, `LOG`), never instructions.

## Therapy

- Exercises are configurable and, by default, not marked
  `clinician_approved`. When `therapy.require_clinician_approval` is true,
  unapproved exercises are still surfaced but flagged as requiring the
  patient's own confirmation, not presented as prescribed treatment.

## When in doubt, seek a clinician

Every generated summary includes an explicit disclaimer. If you or someone
you support is experiencing concerning symptoms, please consult a qualified
clinician — this tool is meant to support that relationship, not replace it.
