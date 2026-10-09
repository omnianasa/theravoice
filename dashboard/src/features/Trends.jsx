import React, { useEffect, useState } from "react";
import { monitoringService } from "../api/services.js";
import { ErrorNotice, Panel, StateMessage, Value, formatDate } from "../components/Common.jsx";

export default function Trends({ patient }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    if (!patient) { setData(null); return undefined; }
    const controller = new AbortController();
    let current = true;
    setLoading(true);
    setError(null);
    setData(null);
    Promise.all([
      monitoringService.biomarkers(patient.id, { signal: controller.signal }),
      monitoringService.events(patient.id, { signal: controller.signal }),
      monitoringService.timeline(patient.id, { signal: controller.signal }),
      monitoringService.clinical(patient.id, { signal: controller.signal }),
    ]).then(([biomarkers, events, timeline, clinical]) => {
      if (current) setData({ patientId: patient.id, biomarkers, events, timeline, clinical });
    }).catch((requestError) => { if (current) setError(requestError); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; controller.abort(); };
  }, [patient?.id, refresh]);

  if (!patient) return <div className="page-stack"><div className="section-intro"><div><p className="eyebrow">Historical records</p><h1>Trends & timeline</h1></div></div><StateMessage title="Select a patient">Patient-specific history is only available after retrieving a patient record.</StateMessage></div>;

  const currentData = data?.patientId === patient.id ? data : null;
  const grouped = (currentData?.biomarkers || []).reduce((groups, item) => {
    (groups[item.name] ||= []).push(item);
    return groups;
  }, {});

  return (
    <div className="page-stack">
      <div className="section-intro section-intro-actions"><div><p className="eyebrow">Historical records</p><h1>Trends & timeline</h1><p className="muted">{patient.display_name} · {patient.id}</p></div>
        <button className="button button-quiet" onClick={() => setRefresh((value) => value + 1)} type="button" disabled={loading}>Refresh history</button></div>
      {error && <ErrorNotice error={error} onRetry={() => setRefresh((value) => value + 1)} />}
      {loading && <StateMessage kind="loading" title="Loading history">Retrieving recorded biomarker values, events, and reports.</StateMessage>}
      {!loading && currentData && (
        <>
          <Panel eyebrow="Persisted values" title="Biomarker history">
            <p className="muted">The current API returns at most 500 records per request and has no date-range or pagination parameters.</p>
            {Object.keys(grouped).length ? <div className="table-wrap"><table><thead><tr><th scope="col">Measurement</th><th scope="col">Value</th><th scope="col">Unit</th><th scope="col">Recorded</th><th scope="col">Source</th></tr></thead>
              <tbody>{Object.entries(grouped).flatMap(([name, records]) => records.map((item, index) => (
                <tr key={`${name}-${item.timestamp}-${index}`}><th scope="row">{name.replaceAll("_", " ")}</th><td><Value value={item.value} available={item.available} reason={item.reason_unavailable} /></td><td>{item.unit || "—"}</td><td>{formatDate(item.timestamp)}</td><td>{item.source || "—"}</td></tr>
              )))}</tbody></table></div> : <StateMessage title="No biomarker history">The API returned no recorded values. Missing measurements are not treated as zero.</StateMessage>}
          </Panel>
          <div className="two-column">
            <Panel eyebrow="Change records" title="Events">
              {currentData.events.length ? <ul className="record-list">{currentData.events.map((event, index) => <li key={`${event.timestamp}-${index}`}><div><strong>{event.type}</strong><span>{event.severity}</span></div><small>{formatDate(event.timestamp)}</small>
                {event.evidence?.map((evidence, evidenceIndex) => <p key={evidenceIndex}>{evidence.description}</p>)}</li>)}</ul> : <StateMessage title="No events">No event records have been returned.</StateMessage>}
            </Panel>
            <Panel eyebrow="Personal-baseline report" title="Clinical summary">
              <p><strong>Baseline status:</strong> {currentData.clinical.baseline_status}</p>
              <p><strong>Observations:</strong> {currentData.clinical.total_observations}</p>
              <p><strong>Period:</strong> {formatDate(currentData.clinical.period_start)} – {formatDate(currentData.clinical.period_end)}</p>
              {currentData.clinical.notes?.length ? <ul className="plain-list">{currentData.clinical.notes.map((note, index) => <li key={index}>{note}</li>)}</ul> : <p className="muted">No report notes.</p>}
              <p className="muted">{currentData.clinical.disclaimer}</p>
            </Panel>
          </div>
          <Panel eyebrow="Recorded activity" title="Timeline">
            {currentData.timeline.entries?.length ? <ol className="timeline">{currentData.timeline.entries.map((entry, index) => <li key={`${entry.timestamp}-${index}`}><time>{formatDate(entry.timestamp)}</time><strong>{entry.kind}</strong><p>{entry.summary}</p></li>)}</ol> : <StateMessage title="Timeline is empty">No historical timeline entries were returned.</StateMessage>}
          </Panel>
        </>
      )}
    </div>
  );
}
