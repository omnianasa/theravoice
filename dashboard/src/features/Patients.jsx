import React, { useState } from "react";
import { patientService } from "../api/services.js";
import { ErrorNotice, Field, Panel, StateMessage, formatDate } from "../components/Common.jsx";

const emptyForm = {
  id: "",
  display_name: "",
  timezone: "UTC",
  consent_data_storage: false,
  consent_audio_analysis: false,
  consent_llm_processing: false,
};

export default function Patients({ patient, onSelectPatient }) {
  const [lookupId, setLookupId] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function lookup(event) {
    event.preventDefault();
    const id = lookupId.trim();
    if (!id) return;
    setError(null);
    setMessage("");
    setBusy(true);
    try {
      const found = await patientService.get(id);
      onSelectPatient(found);
      setMessage(`Loaded ${found.display_name}.`);
    } catch (requestError) {
      setError(requestError);
    } finally {
      setBusy(false);
    }
  }

  async function create(event) {
    event.preventDefault();
    setError(null);
    setMessage("");
    setBusy(true);
    try {
      const created = await patientService.create({
        ...form,
        id: form.id.trim(),
        display_name: form.display_name.trim(),
      });
      onSelectPatient(created);
      setLookupId(created.id);
      setForm(emptyForm);
      setMessage("Patient record created.");
    } catch (requestError) {
      setError(requestError);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-stack">
      <div className="section-intro">
        <div><p className="eyebrow">Patient records</p><h1>Patients</h1>
          <p className="muted">The API supports creating and retrieving a patient by ID, but does not provide a patient-list endpoint. Retrieve a record using an ID you already know.</p></div>
      </div>
      {error && <ErrorNotice error={error} />}
      {message && <p className="inline-success" role="status">{message}</p>}
      <div className="two-column">
        <Panel eyebrow="Existing record" title="Find a patient">
          <form className="stack-form" onSubmit={lookup}>
            <Field label="Patient ID" name="lookup_id" autoComplete="off" value={lookupId} onChange={(event) => setLookupId(event.target.value)} required />
            <button className="button button-primary" disabled={busy || !lookupId.trim()} type="submit">{busy ? "Loading…" : "Retrieve record"}</button>
          </form>
        </Panel>
        <Panel eyebrow="New record" title="Create a patient">
          <form className="stack-form" onSubmit={create}>
            <Field label="Patient ID" name="patient_id" autoComplete="off" value={form.id} onChange={(event) => setForm({ ...form, id: event.target.value })} required maxLength={100} />
            <Field label="Display name" name="display_name" value={form.display_name} onChange={(event) => setForm({ ...form, display_name: event.target.value })} required />
            <Field label="Timezone" name="timezone" value={form.timezone} onChange={(event) => setForm({ ...form, timezone: event.target.value })} required />
            <div className="consent-list">
              <Field type="checkbox" label="Data storage consent" name="consent_data_storage" checked={form.consent_data_storage} onChange={(event) => setForm({ ...form, consent_data_storage: event.target.checked })} hint="Required by default to persist analyses." />
              <Field type="checkbox" label="Audio analysis consent" name="consent_audio_analysis" checked={form.consent_audio_analysis} onChange={(event) => setForm({ ...form, consent_audio_analysis: event.target.checked })} hint="Required to submit audio." />
              <Field type="checkbox" label="LLM processing consent" name="consent_llm_processing" checked={form.consent_llm_processing} onChange={(event) => setForm({ ...form, consent_llm_processing: event.target.checked })} hint="Optional; the backend also requires a configured LLM." />
            </div>
            <button className="button button-primary" disabled={busy} type="submit">{busy ? "Creating…" : "Create patient"}</button>
          </form>
        </Panel>
      </div>
      <Panel eyebrow="Current selection" title="Patient details">
        {patient ? (
          <dl className="detail-grid">
            <div><dt>Display name</dt><dd>{patient.display_name || "Not provided"}</dd></div>
            <div><dt>Patient ID</dt><dd className="monospace">{patient.id}</dd></div>
            <div><dt>Timezone</dt><dd>{patient.timezone || "Not provided"}</dd></div>
            <div><dt>Created</dt><dd>{formatDate(patient.created_at)}</dd></div>
          </dl>
        ) : <StateMessage title="No patient selected">Retrieve a known patient ID or create a record to view patient-specific data.</StateMessage>}
      </Panel>
    </div>
  );
}
