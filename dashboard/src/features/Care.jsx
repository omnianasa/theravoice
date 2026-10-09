import React, { useEffect, useState } from "react";
import { careService, monitoringService } from "../api/services.js";
import { ErrorNotice, Panel, StateMessage, formatDate } from "../components/Common.jsx";

export default function Care({ patient }) {
  const [records, setRecords] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!patient) { setRecords(null); return undefined; }
    const controller = new AbortController();
    let current = true;
    setRecords(null);
    setError(null);
    Promise.all([
      monitoringService.daily(patient.id, null, { signal: controller.signal }),
      careService.schedules(patient.id, { signal: controller.signal }),
      careService.medicationEvents(patient.id, { signal: controller.signal }),
      careService.exercises(patient.id, { signal: controller.signal }),
      careService.recommendations(patient.id, { signal: controller.signal }),
      careService.sessions(patient.id, { signal: controller.signal }),
    ]).then(([daily, schedules, medicationEvents, exercises, recommendations, sessions]) => {
      if (current) setRecords({ patientId: patient.id, daily, schedules, medicationEvents, exercises, recommendations, sessions });
    }).catch((requestError) => { if (current) setError(requestError); });
    return () => { current = false; controller.abort(); };
  }, [patient?.id, refresh]);

  async function startSession(exercise) {
    setError(null);
    setNotice("");
    setBusy(true);
    try {
      await careService.startSession(patient.id, exercise.id);
      setNotice(`Session started for “${exercise.name}”.`);
      setRefresh((value) => value + 1);
    } catch (requestError) {
      setError(requestError);
    } finally {
      setBusy(false);
    }
  }

  if (!patient) return <div className="page-stack"><div className="section-intro"><div><p className="eyebrow">Existing records</p><h1>Reports & care</h1></div></div><StateMessage title="Select a patient">Retrieve a patient record to load reports and care records.</StateMessage></div>;
  const currentRecords = records?.patientId === patient.id ? records : null;

  return (
    <div className="page-stack">
      <div className="section-intro section-intro-actions"><div><p className="eyebrow">Existing records</p><h1>Reports & care</h1><p className="muted">{patient.display_name} · No medication is changed automatically.</p></div>
        <button className="button button-quiet" type="button" onClick={() => setRefresh((value) => value + 1)}>Refresh</button></div>
      {error && <ErrorNotice error={error} onRetry={() => setRefresh((value) => value + 1)} />}
      {notice && <p role="status" className="inline-success">{notice}</p>}
      {!currentRecords && !error && <StateMessage kind="loading" title="Loading reports and care records" />}
      {currentRecords && <>
        <Panel eyebrow="Daily report" title="Summary">
          {currentRecords.daily.observations?.length ? <ul className="plain-list">{currentRecords.daily.observations.map((item, index) => <li key={index}>{item}</li>)}</ul> : <StateMessage title="No observations for this report">The backend returned no daily observations.</StateMessage>}
          {currentRecords.daily.context_notes?.map((item, index) => <p key={index} className="muted">{item}</p>)}
          <p className="muted">{currentRecords.daily.disclaimer}</p>
        </Panel>
        <div className="two-column">
          <Panel eyebrow="Human-entered records" title="Medication schedules">
            {currentRecords.schedules.length ? <ul className="record-list">{currentRecords.schedules.map((item, index) => <li key={`${item.medication_id}-${index}`}><strong>{item.medication_id}</strong><span>{item.scheduled_time} · {item.timezone}</span></li>)}</ul> : <StateMessage title="No schedules recorded">No medication schedules are available.</StateMessage>}
          </Panel>
          <Panel eyebrow="Human-entered records" title="Medication events">
            {currentRecords.medicationEvents.length ? <ul className="record-list">{currentRecords.medicationEvents.map((item, index) => <li key={`${item.id}-${index}`}><strong>{item.status}</strong><span>{item.medication_id}</span><small>{formatDate(item.taken_at)}</small></li>)}</ul> : <StateMessage title="No medication events">No medication events are available.</StateMessage>}
          </Panel>
        </div>
        <Panel eyebrow="Existing non-prescriptive exercises" title="Therapy exercises">
          {currentRecords.exercises.length ? <div className="exercise-grid">{currentRecords.exercises.map((exercise) => <article className="exercise-card" key={exercise.id}>
            <div><h3>{exercise.name}</h3><p>{exercise.description}</p><small>{exercise.duration_seconds} seconds · {exercise.clinician_approved ? "Clinician approved" : "Not marked clinician-approved"}</small></div>
            <ul>{exercise.instructions?.map((instruction, index) => <li key={index}>{instruction}</li>)}</ul>
            <button className="button button-secondary" type="button" disabled={busy || !exercise.clinician_approved} onClick={() => startSession(exercise)}>
              {exercise.clinician_approved ? "Start session" : "Session unavailable"}
            </button>
          </article>)}</div> : <StateMessage title="No exercises available">The exercises endpoint returned no records.</StateMessage>}
          <p className="muted">Recommendations are displayed only if returned by the backend. They are not medical advice.</p>
          {currentRecords.recommendations.length > 0 && <ul className="plain-list">{currentRecords.recommendations.map((exercise) => <li key={exercise.id}>{exercise.name}: {exercise.description}</li>)}</ul>}
        </Panel>
        <Panel eyebrow="Activity log" title="Therapy sessions">
          {currentRecords.sessions.length ? <ul className="record-list">{currentRecords.sessions.map((session) => <li key={session.id}><strong>{session.exercise_id}</strong><span>{session.completed ? "Completed" : "In progress"}</span><small>{formatDate(session.started_at)}</small></li>)}</ul> : <StateMessage title="No sessions recorded">No therapy sessions have been recorded.</StateMessage>}
        </Panel>
      </>}
    </div>
  );
}
