import React, { useEffect, useState } from "react";
import { analysisService } from "../api/services.js";
import { ErrorNotice, Field, Panel, StateMessage, formatDate } from "../components/Common.jsx";

function AnalysisResultView({ result }) {
  return (
    <Panel eyebrow="Backend response" title="Analysis result">
      <div className="result-summary">
        <div><span className="eyebrow">Status</span><strong>{result.status || "Not provided"}</strong></div>
        <div><span className="eyebrow">Baseline status</span><strong>{result.baseline_status || "Not provided"}</strong></div>
        <div><span className="eyebrow">Text length</span><strong>{result.text_length ?? "Not provided"}</strong></div>
      </div>
      <h3>Biomarkers returned</h3>
      {result.biomarkers && Object.keys(result.biomarkers).length ? (
        <div className="metric-grid">
          {Object.entries(result.biomarkers).map(([name, value]) => (
            <div className="metric-tile" key={name}><span>{name.replaceAll("_", " ")}</span>
              <strong>{value === null || value === undefined ? "Unavailable" : value}</strong></div>
          ))}
        </div>
      ) : <StateMessage title="No biomarker values returned">This response contains no biomarker measurements.</StateMessage>}
      {result.events?.length > 0 && <><h3>Observed events</h3><pre className="structured-data">{JSON.stringify(result.events, null, 2)}</pre></>}
      {result.actions?.length > 0 && <><h3>Assistive actions</h3><pre className="structured-data">{JSON.stringify(result.actions, null, 2)}</pre></>}
      <p className="muted">Analysis returned for patient {result.patient_id || "not identified"}{result.timestamp ? ` · ${formatDate(result.timestamp)}` : ""}. Results are descriptive and not a diagnosis.</p>
    </Panel>
  );
}

export default function Analysis({ patient }) {
  const [mode, setMode] = useState("transcript");
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const visibleResult = result?.patient_id === patient?.id ? result : null;

  useEffect(() => {
    setResult(null);
    setError(null);
    setText("");
    setFile(null);
  }, [patient?.id]);

  async function submit(event) {
    event.preventDefault();
    setError(null);
    setResult(null);
    if (!patient) {
      setError(new Error("Select a patient before submitting an analysis."));
      return;
    }
    if (!patient.consent_data_storage) {
      setError(new Error("This patient has not granted data-storage consent. The backend may reject analysis."));
      return;
    }
    if (mode === "audio" && !patient.consent_audio_analysis) {
      setError(new Error("Audio analysis consent has not been granted for this patient."));
      return;
    }
    if (mode === "transcript" && !text.trim()) {
      setError(new Error("Enter a transcript before submitting."));
      return;
    }
    if (mode === "audio" && !file) {
      setError(new Error("Select an audio file before submitting."));
      return;
    }
    setBusy(true);
    try {
      const response = mode === "transcript"
        ? await analysisService.transcript(patient.id, text.trim())
        : await analysisService.audio(patient.id, file, text);
      setResult(response);
    } catch (requestError) {
      setError(requestError);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-stack">
      <div className="section-intro"><div><p className="eyebrow">Speech processing</p><h1>Speech analysis</h1>
        <p className="muted">Submit a transcript or audio file to TheraVoice. Analysis runs on the configured backend; this browser never contacts an LLM provider.</p></div></div>
      <Panel eyebrow="New analysis" title="Analysis workspace">
        {!patient ? <StateMessage title="Select a patient">Use Patients to retrieve or create a record first.</StateMessage> : (
          <>
            <div className="selected-patient"><span>Selected patient</span><strong>{patient.display_name}</strong><small>{patient.id}</small></div>
            <div className="segmented-control" role="group" aria-label="Analysis type">
              <button type="button" aria-pressed={mode === "transcript"} onClick={() => { setMode("transcript"); setError(null); }}>Transcript</button>
              <button type="button" aria-pressed={mode === "audio"} onClick={() => { setMode("audio"); setError(null); }}>Audio file</button>
            </div>
            {!patient.consent_data_storage && <StateMessage kind="error" title="Data-storage consent is off">The backend requires storage consent before it persists analysis data.</StateMessage>}
            {mode === "audio" && !patient.consent_audio_analysis && <StateMessage kind="error" title="Audio consent is off">Audio submission is unavailable until this patient has granted audio-analysis consent.</StateMessage>}
            {error && <ErrorNotice error={error} />}
            <form className="stack-form" onSubmit={submit}>
              {mode === "transcript" ? (
                <div className="field">
                  <label htmlFor="transcript">Transcript</label>
                  <textarea id="transcript" rows="7" value={text} onChange={(event) => setText(event.target.value)} required aria-describedby="transcript-note" />
                  <small id="transcript-note">Text is submitted to the TheraVoice backend. Avoid including information that is not needed for this analysis.</small>
                </div>
              ) : (
                <>
                  <div className="field"><label htmlFor="audio-file">Audio file</label>
                    <input id="audio-file" type="file" accept="audio/*,.wav,.flac,.ogg,.mp3" onChange={(event) => setFile(event.target.files?.[0] || null)} required />
                    <small>Backend decoder support depends on installed audio libraries. No server-side file-size limit is documented. Uploaded audio is processed by the backend; raw-audio storage defaults to off.</small></div>
                  <div className="field"><label htmlFor="audio-context">Optional transcript</label>
                    <textarea id="audio-context" rows="4" value={text} onChange={(event) => setText(event.target.value)} /></div>
                </>
              )}
              <button className="button button-primary" disabled={busy || !patient.consent_data_storage || (mode === "audio" && !patient.consent_audio_analysis)} type="submit">
                {busy ? "Analyzing…" : "Submit for analysis"}
              </button>
            </form>
          </>
        )}
      </Panel>
      {visibleResult && <AnalysisResultView result={visibleResult} />}
    </div>
  );
}
