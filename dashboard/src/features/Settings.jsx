import React, { useEffect, useState } from "react";
import { integrationService, patientService, monitoringService } from "../api/services.js";
import { ErrorNotice, Panel, StateMessage } from "../components/Common.jsx";

export default function Settings({ user, patient, onPatientUpdated, onLogout }) {
  const [integration, setIntegration] = useState(null);
  const [apiInfo, setApiInfo] = useState(null);
  const [beeStatus, setBeeStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [savingConsent, setSavingConsent] = useState(false);
  const [consent, setConsent] = useState(false);
  const [consentPatientId, setConsentPatientId] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let current = true;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    const requests = [
      monitoringService.integrations({ signal: controller.signal }),
      monitoringService.info({ signal: controller.signal }),
    ];
    if (patient) requests.push(integrationService.beeStatus(patient.id, { signal: controller.signal }));
    Promise.all(requests).then(([integrationResponse, info, status]) => {
      if (!current) return;
      setIntegration(integrationResponse);
      setApiInfo(info);
      setBeeStatus(status ? { ...status, _patientId: patient?.id } : null);
      setConsent(patient?.consent_llm_processing || false);
      setConsentPatientId(patient?.id || null);
    }).catch((requestError) => { if (current) setError(requestError); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; controller.abort(); };
  }, [patient?.id, patient?.consent_llm_processing]);

  const consentValue = consentPatientId === patient?.id
    ? consent
    : patient?.consent_llm_processing || false;

  async function saveConsent(event) {
    event.preventDefault();
    setError(null);
    setNotice("");
    setSavingConsent(true);
    try {
      const updated = await patientService.updateLlmConsent(patient.id, consentValue);
      onPatientUpdated(updated);
      setNotice("Patient LLM-processing consent updated.");
    } catch (requestError) {
      setError(requestError);
    } finally {
      setSavingConsent(false);
    }
  }

  async function syncBee() {
    if (syncing || !patient) return;
    setError(null);
    setNotice("");
    setSyncing(true);
    try {
      const response = await integrationService.beeSync(patient.id);
      setNotice(response.message);
      setBeeStatus({ ...await integrationService.beeStatus(patient.id), _patientId: patient.id });
    } catch (requestError) {
      setError(requestError);
      try { setBeeStatus({ ...await integrationService.beeStatus(patient.id), _patientId: patient.id }); } catch { /* Preserve the original sync error. */ }
    } finally {
      setSyncing(false);
    }
  }

  const bee = integration?.integrations?.find((item) => item.name === "bee");

  return (
    <div className="page-stack">
      <div className="section-intro"><div><p className="eyebrow">Account & connections</p><h1>Settings & integrations</h1><p className="muted">Service-reported configuration only; the dashboard never displays provider credentials.</p></div></div>
      {error && <ErrorNotice error={error} />}
      {notice && <p className="inline-success" role="status">{notice}</p>}
      <div className="two-column">
        <Panel eyebrow="Signed-in account" title="Account">
          <dl className="detail-grid"><div><dt>Name</dt><dd>{user?.display_name || "—"}</dd></div><div><dt>Email</dt><dd>{user?.email || "—"}</dd></div></dl>
          <button className="button button-secondary" onClick={onLogout} type="button">Sign out</button>
        </Panel>
        <Panel eyebrow="Backend configuration" title="Bee integration">
          {loading && <StateMessage kind="loading" title="Checking reported configuration" />}
          {!loading && bee && <div className="integration-card">
            <div><strong>Mode</strong><span>{bee.mode}</span></div>
            <div><strong>Configured</strong><span>{bee.configured ? "Yes" : "No"}</span></div>
            <div><strong>Enabled</strong><span>{bee.enabled ? "Yes" : "No"}</span></div>
            <p className="muted">Configuration does not confirm that Bee CLI, export files, or proxy connectivity have been tested.</p>
          </div>}
          {!loading && !bee && <StateMessage title="Bee status unavailable">The backend did not return a Bee integration status.</StateMessage>}
          {patient && beeStatus?._patientId === patient.id && <div className="integration-card patient-integration">
            <div><strong>Patient sync status</strong><span>{beeStatus.status}</span></div>
            <div><strong>Source configured</strong><span>{beeStatus.source_configured ? "Yes" : "No"}</span></div>
            {beeStatus.last_successful_sync_at && <div><strong>Last successful sync</strong><span>{new Date(beeStatus.last_successful_sync_at).toLocaleString()}</span></div>}
            {beeStatus.error_code && <div><strong>Last error code</strong><span>{beeStatus.error_code}</span></div>}
            <button className="button button-primary" type="button" onClick={syncBee} disabled={syncing || !beeStatus.source_configured}>
              {syncing ? "Synchronizing…" : "Synchronize from Bee"}
            </button>
            {!beeStatus.source_configured && <p className="muted">Configure an operator-managed source-to-patient binding on the backend before syncing.</p>}
          </div>}
        </Panel>
      </div>
      <Panel eyebrow="Patient-specific preference" title="LLM processing consent">
        {!patient ? <StateMessage title="Select a patient">Retrieve a patient to view or change that patient’s LLM processing consent.</StateMessage> : <>
          <p className="muted">This changes only the existing patient consent flag. Consent does not enable an LLM by itself; provider configuration remains server-side. No provider key is sent or stored by this page.</p>
          <form className="consent-save" onSubmit={saveConsent}>
            <label className="checkbox-field"><input type="checkbox" checked={consentValue} onChange={(event) => { setConsent(event.target.checked); setConsentPatientId(patient.id); }} /><span>Allow LLM-assisted summary processing for {patient.display_name}</span></label>
            <button className="button button-secondary" type="submit" disabled={savingConsent || consentValue === patient.consent_llm_processing}>{savingConsent ? "Saving…" : "Save consent"}</button>
          </form>
        </>}
      </Panel>
      <div className="two-column">
        <Panel eyebrow="Not exposed by current API" title="LLM provider">
          <StateMessage title="Provider status unavailable">There is no public endpoint reporting LLM provider configuration. Provider name, model, and credentials are not inferred from consent.</StateMessage>
        </Panel>
        <Panel eyebrow="Not exposed by current API" title="AWS integration">
          <StateMessage title="AWS status unavailable">The backend does not expose AWS connection status. No connection is assumed.</StateMessage>
        </Panel>
      </div>
      <Panel eyebrow="Data source" title="API and release information">
        {apiInfo && <p>API {apiInfo.api_version} · TheraVoice {apiInfo.version}</p>}
        {!apiInfo && !loading && <p className="muted">API release information is unavailable.</p>}
        <p className="muted">Account sessions expire after 12 hours. The access token is held in tab-scoped session storage to survive refresh, and is removed on logout or an unauthorized response.</p>
      </Panel>
    </div>
  );
}
