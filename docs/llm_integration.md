# LLM Integration

TheraVoice can use OpenAI or Google Gemini to write the daily summary. The
integration is disabled by default. Biomarker extraction, event detection,
medication handling, and therapy recommendations remain deterministic and
do not use an LLM.

## Enable a Provider

Set the provider and API key in the process environment. For example, in
PowerShell:

```powershell
$env:THERAVOICE_LLM_PROVIDER = "openai"
$env:THERAVOICE_LLM_MODEL = "gpt-4o-mini"
$env:THERAVOICE_LLM_API_KEY = "<provider-api-key>"
theravoice serve --reload
```

For Gemini, use `gemini` as the provider and optionally set
`THERAVOICE_LLM_MODEL` (the default is `gemini-2.0-flash`). OpenAI defaults to
`gpt-4o-mini`. The YAML `llm` section can select the provider, model, and
positive request timeout; environment variables override those values. Leave
the provider as `none` to use deterministic summaries. If a key is missing,
the provider is unknown, or a request fails or times out, TheraVoice falls
back to the deterministic summary.
The ingestion response's `context.summary_generation_status` is `generated`,
`fallback`, or `deterministic`; on provider failure,
`context.summary_generation_error` is the stable code `provider_failure`.
The provider's raw error is kept in server logs and is not returned to clients.

Provider requests currently use synchronous HTTP clients. The configured
timeout bounds each request but does not release the request worker while it
waits. High-throughput deployments should account for this; asynchronous
clients, concurrency limits, and provider-specific retry/rate-limit handling
are not implemented yet.

## Data Handling

When enabled, the summary agent sends only its structured observations,
context notes, and suggested-action messages to the selected provider. It does
not send the patient ID or raw transcript. Generation is additionally gated
by the patient's separate `consent_llm_processing` flag, which defaults to
false. Set it during `POST /patients` or update/revoke it with
`PATCH /patients/{patient_id}/consent` using
`{"consent_llm_processing": true|false}`. Existing databases receive the new
column with consent disabled by default at startup. These summary fields can
still contain sensitive health information. Configure an external provider
only when organizational policy and provider data handling terms permit that
transfer. API keys must be supplied through a secret manager or environment
variable, never committed to YAML or source control.

Generated text is used only for the human-readable summary. Required
non-diagnostic language is appended by the application, and generated output
does not determine events, medication actions, or therapy recommendations.