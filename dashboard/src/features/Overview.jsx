import React, { useEffect, useState } from "react";
import { monitoringService } from "../api/services.js";
import { ErrorNotice, Panel, StateMessage, Value, formatDate } from "../components/Common.jsx";

function FeatureMonitor({ user, patient, integrations, onNavigate }) {
  const bee = integrations?.integrations?.find((item) => item.name === "bee");
  const patientState = patient ? "Record selected" : "Needs a patient";
  const ingestionState = !patient
    ? "Needs a patient"
    : patient.consent_data_storage
      ? patient.consent_audio_analysis
        ? "Consent permits transcript and audio"
        : "Audio consent required"
      : "Storage consent required";
  const beeState = !bee
    ? "Not reported"
    : bee.mode === "mock"
      ? "Mock test mode"
      : `Configured mode: ${bee.mode}`;

  const workflows = [
    {
      title: "Sign in & create an account",
      state: user ? "Session active" : "Sign-in required",
      detail: "Account identity comes from the authentication API response. Registration, login, and logout use the existing auth operations.",
      action: null,
    },
    {
      title: "Create or retrieve a patient",
      state: patientState,
      detail: patient
        ? `${patient.display_name} · ${patient.id}. The API does not expose a patient-list endpoint.`
        : "Create a record or retrieve one by a known ID. The API does not expose a patient-list endpoint.",
      action: ["Patients", "patients"],
    },
    {
      title: "Ingest transcript or audio",
      state: ingestionState,
      detail: patient
        ? "Transcript uses the JSON analysis operation; audio uses multipart upload. The backend enforces consent."
        : "The API provides transcript and multipart audio operations. A patient and the relevant consent are required.",
      action: ["Open analysis", "analysis"],
    },
    {
      title: "Monitor history & reports",
      state: patient ? "Patient data available to query" : "Needs a patient",
      detail: "Biomarkers, events, timeline, daily and clinical reports come from patient-scoped API reads; no records are fabricated.",
      action: ["View history", "trends"],
    },
    {
      title: "Medication & therapy records",
      state: patient ? "Patient data available to query" : "Needs a patient",
      detail: "Schedules, medication events, exercises, recommendations, and sessions are loaded from existing API operations.",
      action: ["Open care", "care"],
    },
    {
      title: "Bee ingestion",
      state: beeState,
      detail: bee?.mode === "mock"
        ? "The backend reports its mock adapter. A manual sync is a safe test of the sync flow and may return no conversations; it is not live Bee data."
        : "The backend reports configuration only. Use Settings for an explicit sync; configuration alone does not verify CLI login, source binding, or connectivity.",
      action: ["Bee settings", "settings"],
    },
  ];

  return (
    <Panel eyebrow="Feature-by-feature status" title="Application workflow monitor" className="feature-monitor">
      <p className="muted">Statuses below are derived from the current account, selected patient, and service-reported configuration. They are not background activity logs or clinical assessments.</p>
      <div className="workflow-list">
        {workflows.map((workflow) => (
          <article className="workflow-row" key={workflow.title}>
            <div className="workflow-copy">
              <h3>{workflow.title}</h3>
              <span className={`workflow-state ${workflow.state === "Mock test mode" ? "workflow-test" : ""}`}>{workflow.state}</span>
              <p>{workflow.detail}</p>
            </div>
            {workflow.action && (
              <button className="button button-quiet" onClick={() => onNavigate(workflow.action[1])} type="button">
                {workflow.action[0]}
              </button>
            )}
          </article>
        ))}
      </div>
      <p className="monitor-note">To verify Bee with real data, an operator must configure a source-to-patient binding and an authenticated local Bee CLI/proxy or export. No sync is triggered automatically.</p>
    </Panel>
  );
}

export default function Overview({ user, patient, onNavigate }) {
  const [system, setSystem] = useState(null);
  const [patientData, setPatientData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    setLoading(true);
    setError(null);
    const fetchSystem = Promise.all([
      monitoringService.health({ signal: controller.signal }),
      monitoringService.info({ signal: controller.signal }),
      monitoringService.integrations({ signal: controller.signal }),
    ]);
    const fetchPatient = patient
      ? Promise.all([
          monitoringService.latestBiomarkers(patient.id, { signal: controller.signal }),
          monitoringService.events(patient.id, { signal: controller.signal }),
          monitoringService.daily(patient.id, null, { signal: controller.signal }),
        ])
      : Promise.resolve(null);
    Promise.all([fetchSystem, fetchPatient])
      .then(([systemValues, patientValues]) => {
        if (!current) return;
        setSystem({ health: systemValues[0], info: systemValues[1], integrations: systemValues[2] });
        setPatientData(patientValues ? { patientId: patient?.id, biomarkers: patientValues[0], events: patientValues[1], daily: patientValues[2] } : null);
      })
      .catch((requestError) => { if (current) setError(requestError); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; controller.abort(); };
  }, [patient?.id, refresh]);

  return (
    <div className="page-stack">
      <div className="section-intro section-intro-actions">
        <div><p className="eyebrow">Monitoring workspace</p><h1>Overview</h1><p className="muted">A factual summary of records returned by the TheraVoice service.</p></div>
        <button className="button button-quiet" type="button" onClick={() => setRefresh((value) => value + 1)} disabled={loading}>Refresh</button>
      </div>
      {error && <ErrorNotice error={error} onRetry={() => setRefresh((value) => value + 1)} />}
      {loading && <StateMessage kind="loading" title="Loading service data">Fetching health, API information, and configured integration status.</StateMessage>}
      {!loading && system && (
        <div className="summary-grid" aria-label="Live service checks">
          <Panel eyebrow="API availability" title={system.health?.status === "ok" ? "Service responding" : "Status unavailable"}>
            <p className="muted">{system.health?.service || "TheraVoice API"}</p>
          </Panel>
          <Panel eyebrow="Release" title={`Version ${system.info?.version || "unknown"}`}>
            <p className="muted">API {system.info?.api_version || "version unavailable"}</p>
          </Panel>
          <Panel eyebrow="Configured adapters" title={`${system.integrations?.integrations?.length || 0} reported`}>
            <p className="muted">Configuration is not proof of a live external connection.</p>
          </Panel>
        </div>
      )}
      {!loading && system && <FeatureMonitor user={user} patient={patient} integrations={system.integrations} onNavigate={onNavigate} />}
      {patient ? (
        <>
          <div className="section-intro compact"><div><p className="eyebrow">Selected record</p><h2>{patient.display_name}</h2><p className="muted monospace">{patient.id}</p></div></div>
          {loading && <StateMessage kind="loading" title="Loading patient summary" />}
          {!loading && patientData?.patientId === patient.id && (
            <div className="two-column">
              <Panel eyebrow="Latest recorded values" title="Biomarkers">
                {patientData.biomarkers?.values?.length ? (
                  <div className="metric-grid">{patientData.biomarkers.values.map((item) => (
                    <div className="metric-tile" key={`${item.name}-${item.timestamp}`}>
                      <span>{item.name.replaceAll("_", " ")}</span>
                      <strong><Value value={item.value} available={item.available} reason={item.reason_unavailable} /> {item.available ? item.unit || "" : ""}</strong>
                      <small>{formatDate(item.timestamp)}</small>
                    </div>
                  ))}</div>
                ) : <StateMessage title="No biomarker snapshot">No latest biomarker measurements are available for this patient.</StateMessage>}
              </Panel>
              <Panel eyebrow="Recorded observations" title="Recent events">
                {patientData.events?.length ? <ul className="record-list">{patientData.events.slice(0, 5).map((event, index) => (
                  <li key={`${event.timestamp}-${index}`}><div><strong>{event.type}</strong><span>{event.severity.replaceAll("_", " ")}</span></div><small>{formatDate(event.timestamp)}</small></li>
                ))}</ul> : <StateMessage title="No events recorded">The events endpoint returned no records.</StateMessage>}
                <button className="button button-quiet" onClick={() => onNavigate("trends")} type="button">View history</button>
              </Panel>
            </div>
          )}
          {!loading && patientData?.patientId === patient.id && patientData.daily && (
            <Panel eyebrow="Backend daily report" title="Today’s summary">
              {patientData.daily.observations?.length ? <ul className="plain-list">{patientData.daily.observations.map((note, i) => <li key={i}>{note}</li>)}</ul> : <StateMessage title="No daily observations">The report contains no observation summaries for the current day.</StateMessage>}
              <p className="muted">{patientData.daily.disclaimer}</p>
            </Panel>
          )}
        </>
      ) : (
        <Panel eyebrow="Patient data" title="No patient selected">
          <StateMessage title="Start with a patient record">There is no patient-list endpoint. Retrieve a patient using a known ID or create a record; this dashboard will not fabricate patients.</StateMessage>
          <button className="button button-primary" onClick={() => onNavigate("patients")} type="button">Open patients</button>
        </Panel>
      )}
      <footer className="disclaimer">{system?.info?.disclaimer || "TheraVoice outputs are descriptive, not diagnostic, and do not replace professional medical judgment."}</footer>
    </div>
  );
}
