import { useEffect, useState } from "react";
import brandArtwork from "../../assets/black.png";
import brandArtworkwhite from "../../assets/white.png";

const queryApi = new URLSearchParams(window.location.search).get("api");
const API_BASE = (queryApi || import.meta.env.VITE_API_BASE || "").replace(/\/+$/, "");
const TOKEN_STORAGE_KEY = "theravoice.accessToken";

async function apiFetch(path, options = {}, token = null) {
    const headers = new Headers(options.headers || {});
    if (typeof options.body === "string" && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
    }
    if (token) headers.set("Authorization", `Bearer ${token}`);

    const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
    const body = response.status === 204 ? null : await response.json().catch(() => null);
    if (!response.ok) {
        const message = body?.detail || (response.status === 401 ? "Your session has expired. Sign in again." : response.statusText);
        throw new Error(message);
    }
    return body;
}

function formatDate(value) {
    const date = new Date(value);
    return Number.isNaN(date.valueOf()) ? "" : date.toLocaleString();
}

function Empty({ children }) {
    return <p className="muted">{children}</p>;
}

function AuthPanel({ onAuthenticated }) {
    const [mode, setMode] = useState("login");
    const [email, setEmail] = useState("");
    const [displayName, setDisplayName] = useState("");
    const [password, setPassword] = useState("");
    const [message, setMessage] = useState("");
    const [busy, setBusy] = useState(false);

    async function submit(event) {
        event.preventDefault();
        setMessage("");
        setBusy(true);
        try {
            const path = mode === "register" ? "/auth/register" : "/auth/login";
            const payload = { email, password };
            if (mode === "register") payload.display_name = displayName;
            const session = await apiFetch(path, { method: "POST", body: JSON.stringify(payload) });
            onAuthenticated(session);
        } catch (error) {
            setMessage(error.message);
        } finally {
            setBusy(false);
        }
    }

    return (
        <main className="auth-layout">
            <section className="auth-intro">
                <img className="auth-brand-artwork" src={brandArtworkwhite} alt="TheraVoice owl and wordmark" />
                <p className="eyebrow">A personal communication companion</p>
                <h1>Understand change, one day at a time.</h1>
                <p className="auth-description">TheraVoice observes speech and language patterns over time, comparing each person's communication with their own history.</p>
                <div className="profile-principles">
                    <span>Personal baseline</span>
                    <span>Descriptive summaries</span>
                    <span>Never a diagnosis</span>
                </div>
                <p className="auth-note">Each account has a private workspace. Patient records are only available to the account that created them.</p>
            </section>
            <section className="card auth-card" aria-labelledby="auth-heading">
                <div className="auth-tabs" role="tablist" aria-label="Account access">
                    <button className={mode === "login" ? "active" : "secondary"} type="button" onClick={() => setMode("login")}>Sign in</button>
                    <button className={mode === "register" ? "active" : "secondary"} type="button" onClick={() => setMode("register")}>Sign up</button>
                </div>
                <h2 id="auth-heading">{mode === "register" ? "Create your account" : "Welcome back"}</h2>
                <form className="stack" onSubmit={submit}>
                    {mode === "register" && <label>Full name<input autoComplete="name" maxLength="120" required value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>}
                    <label>Email<input autoComplete="email" type="email" maxLength="254" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
                    <label>Password<input autoComplete={mode === "register" ? "new-password" : "current-password"} type="password" minLength={mode === "register" ? 12 : 1} maxLength="128" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
                    {mode === "register" && <p className="muted">Use at least 12 characters.</p>}
                    {message && <p className="status error" role="alert">{message}</p>}
                    <button type="submit" disabled={busy}>{busy ? "Please wait…" : mode === "register" ? "Create account" : "Sign in"}</button>
                </form>
            </section>
        </main>
    );
}

function AuthenticatedDashboard({ token, user, onSignOut }) {
    const savedIdKey = `theravoice.lastPatientId.${user.id}`;
    const [patientId, setPatientId] = useState(() => window.localStorage.getItem(savedIdKey) || "");
    const [patientRecord, setPatientRecord] = useState(null);
    const [patientName, setPatientName] = useState("");
    const [consentStorage, setConsentStorage] = useState(false);
    const [consentAudio, setConsentAudio] = useState(false);
    const [consentLlm, setConsentLlm] = useState(false);
    const [patientLlmConsent, setPatientLlmConsent] = useState(false);
    const [llmProvider, setLlmProvider] = useState("server");
    const [llmModel, setLlmModel] = useState("");
    const [llmApiKey, setLlmApiKey] = useState("");
    const [llmSessionConfig, setLlmSessionConfig] = useState(null);
    const [showApiKey, setShowApiKey] = useState(false);
    const [transcript, setTranscript] = useState("");
    const [analysisResult, setAnalysisResult] = useState(null);
    const [data, setData] = useState({ biomarkers: null, daily: null, events: [], timeline: null });
    const [status, setStatus] = useState("");
    const [isError, setIsError] = useState(false);
    const [busy, setBusy] = useState("");

    useEffect(() => {
        if (patientId) window.localStorage.setItem(savedIdKey, patientId);
        else window.localStorage.removeItem(savedIdKey);
    }, [patientId, savedIdKey]);

    async function loadPatientData(id = patientId) {
        const normalizedId = id.trim();
        if (!normalizedId) {
            setStatus("Enter a patient ID first.");
            setIsError(true);
            return;
        }
        setBusy("load");
        setStatus("Loading patient data…");
        setIsError(false);
        try {
            const patient = await apiFetch(`/patients/${encodeURIComponent(normalizedId)}`, {}, token);
            const [biomarkers, daily, events, timeline] = await Promise.all([
                apiFetch(`/patients/${encodeURIComponent(normalizedId)}/biomarkers/latest`, {}, token).catch(() => null),
                apiFetch(`/patients/${encodeURIComponent(normalizedId)}/reports/daily`, {}, token).catch(() => null),
                apiFetch(`/patients/${encodeURIComponent(normalizedId)}/events`, {}, token).catch(() => []),
                apiFetch(`/patients/${encodeURIComponent(normalizedId)}/reports/timeline`, {}, token).catch(() => null),
            ]);
            if (patientRecord?.id !== normalizedId) {
                setLlmProvider("server");
                setLlmModel("");
                setLlmApiKey("");
                setLlmSessionConfig(null);
                setShowApiKey(false);
            }
            setPatientRecord(patient);
            setPatientLlmConsent(patient.consent_llm_processing);
            setPatientId(normalizedId);
            setData({ biomarkers, daily, events, timeline });
            setStatus(`Loaded ${normalizedId}.`);
        } catch (error) {
            setStatus(error.message);
            setIsError(true);
        } finally {
            setBusy("");
        }
    }

    async function savePatientLlmSettings(event) {
        event.preventDefault();
        if (!patientRecord) return;

        const normalizedKey = llmApiKey.trim();
        if (patientLlmConsent && llmProvider !== "server" && !normalizedKey) {
            setStatus("Add the selected provider's API key before enabling summaries.");
            setIsError(true);
            return;
        }

        setBusy("llm");
        setStatus("Saving patient AI settings…");
        setIsError(false);
        try {
            const updatedPatient = await apiFetch(
                `/patients/${encodeURIComponent(patientRecord.id)}/consent`,
                {
                    method: "PATCH",
                    body: JSON.stringify({ consent_llm_processing: patientLlmConsent }),
                },
                token,
            );
            setPatientRecord(updatedPatient);
            setPatientLlmConsent(updatedPatient.consent_llm_processing);
            if (!updatedPatient.consent_llm_processing || llmProvider === "server") {
                setLlmApiKey("");
            }
            setLlmSessionConfig(
                updatedPatient.consent_llm_processing && llmProvider !== "server"
                    ? { provider: llmProvider, model: llmModel.trim(), apiKey: normalizedKey }
                    : null,
            );
            setStatus(
                updatedPatient.consent_llm_processing
                    ? llmProvider === "server"
                        ? "Consent saved. Summaries will use the server's LLM configuration, if enabled."
                        : "Consent saved. This provider key is active for this browser session only."
                    : "LLM summary consent is off for this patient.",
            );
        } catch (error) {
            setStatus(error.message);
            setIsError(true);
        } finally {
            setBusy("");
        }
    }

    async function createPatient(event) {
        event.preventDefault();
        if (!consentStorage) {
            setStatus("Confirm data-storage consent before creating this patient.");
            setIsError(true);
            return;
        }
        const id = patientId.trim();
        if (!id || !patientName.trim()) {
            setStatus("Enter a patient ID and display name.");
            setIsError(true);
            return;
        }
        setBusy("create");
        setStatus("Creating patient…");
        setIsError(false);
        try {
            await apiFetch("/patients", {
                method: "POST",
                body: JSON.stringify({
                    id,
                    display_name: patientName.trim(),
                    consent_data_storage: consentStorage,
                    consent_audio_analysis: consentAudio,
                    consent_llm_processing: consentLlm,
                }),
            }, token);
            setPatientName("");
            setStatus(`Created ${id}.`);
            await loadPatientData(id);
        } catch (error) {
            setStatus(error.message);
            setIsError(true);
        } finally {
            setBusy("");
        }
    }

    async function syncBee() {
        const id = patientId.trim();
        if (!id) {
            setStatus("Enter a patient ID first.");
            setIsError(true);
            return;
        }
        setBusy("sync");
        setStatus("Syncing from Bee…");
        setIsError(false);
        try {
            const result = await apiFetch(`/patients/${encodeURIComponent(id)}/bee/sync`, { method: "POST" }, token);
            setStatus(result.message);
            await loadPatientData(id);
        } catch (error) {
            setStatus(error.message);
            setIsError(true);
        } finally {
            setBusy("");
        }
    }

    async function analyzeTranscript(event) {
        event.preventDefault();
        const id = patientId.trim();
        if (!id || !transcript.trim()) {
            setStatus("Enter a patient ID and transcript text.");
            setIsError(true);
            return;
        }
        if (patientRecord?.consent_llm_processing !== patientLlmConsent) {
            setStatus("Save the patient's LLM consent setting before analyzing.");
            setIsError(true);
            return;
        }
        if (patientLlmConsent && llmProvider !== "server" && !llmSessionConfig) {
            setStatus("Save the provider settings before analyzing with an LLM.");
            setIsError(true);
            return;
        }
        setBusy("analyze");
        setStatus("Analyzing transcript…");
        setIsError(false);
        try {
            const headers = llmSessionConfig && patientLlmConsent
                ? {
                    "X-TheraVoice-LLM-Provider": llmSessionConfig.provider,
                    "X-TheraVoice-LLM-Model": llmSessionConfig.model,
                    "X-TheraVoice-LLM-API-Key": llmSessionConfig.apiKey,
                }
                : undefined;
            const result = await apiFetch("/ingestion/transcript", {
                method: "POST",
                headers,
                body: JSON.stringify({ patient_id: id, text: transcript.trim() }),
            }, token);
            setAnalysisResult(result);
            setStatus("Analysis complete.");
            await loadPatientData(id);
        } catch (error) {
            setStatus(error.message);
            setIsError(true);
        } finally {
            setBusy("");
        }
    }

    return (
        <>
            <header className="app-header">
                <div className="brand-lockup"><img src={brandArtworkwhite} alt="TheraVoice" /><span>Personal communication monitoring</span></div>
                <div className="account-actions"><span>{user.display_name}</span><button className="secondary" type="button" onClick={onSignOut}>Sign out</button></div>
            </header>
            <main className="dashboard-main">
                <section className="product-profile" aria-labelledby="profile-heading">
                    <div className="product-profile-copy">
                        <p className="eyebrow">TheraVoice profile</p>
                        <h1 id="profile-heading">Communication, understood in context.</h1>
                        <p>TheraVoice is an assistive monitoring companion. It tracks descriptive speech and language signals against a person's own baseline, then brings observations together as summaries and optional check-in suggestions.</p>
                        <div className="profile-principles">
                            <span>Personal history, not population norms</span>
                            <span>Transparent observations</span>
                            <span>No diagnosis or medication changes</span>
                        </div>
                    </div>
                    <div className="profile-artwork"><img src={brandArtwork} alt="TheraVoice owl with a speech waveform" /></div>
                </section>

                <div className="workspace-heading">
                    <div><p className="eyebrow">Your workspace</p><h2>Patient</h2></div>
                    <p>Load an existing record or create a new one.</p>
                </div>
                <section className="card patient-picker">
                    <div className="patient-tools">
                        <label>Patient ID<input value={patientId} onChange={(event) => setPatientId(event.target.value)} placeholder="patient-demo-001" /></label>
                        <div className="button-row"><button type="button" disabled={Boolean(busy)} onClick={() => loadPatientData()}>Load</button><button className="secondary" type="button" disabled={Boolean(busy)} onClick={syncBee}>Sync from Bee</button></div>
                    </div>
                    <p className={`status${isError ? " error" : ""}`} role="status">{status}</p>
                </section>

                <section className="consent-banner"><strong>Non-diagnostic, assistive tool.</strong> TheraVoice compares observations with a person's own historical baseline. It does not diagnose or change medication.</section>

                <section className="card create-patient">
                    <div><p className="eyebrow">New record</p><h2>Create a patient</h2></div>
                    <form className="create-patient-form" onSubmit={createPatient}>
                        <label>Patient ID<input value={patientId} onChange={(event) => setPatientId(event.target.value)} maxLength="120" required /></label>
                        <label>Display name<input value={patientName} onChange={(event) => setPatientName(event.target.value)} maxLength="120" required /></label>
                        <div className="consent-options">
                            <label className="check-label"><input type="checkbox" checked={consentStorage} onChange={(event) => setConsentStorage(event.target.checked)} /> Data storage consent (required)</label>
                            <label className="check-label"><input type="checkbox" checked={consentAudio} onChange={(event) => setConsentAudio(event.target.checked)} /> Audio analysis consent</label>
                            <label className="check-label"><input type="checkbox" checked={consentLlm} onChange={(event) => setConsentLlm(event.target.checked)} /> LLM summary consent</label>
                        </div>
                        <button type="submit" disabled={Boolean(busy)}>Create patient</button>
                    </form>
                </section>

                {patientRecord && <section className="card patient-profile" aria-labelledby="patient-profile-heading">
                    <div className="patient-profile-heading">
                        <div><p className="eyebrow">Patient profile</p><h2 id="patient-profile-heading">{patientRecord.display_name}</h2></div>
                        <span className="patient-id">{patientRecord.id}</span>
                    </div>
                    <form className="llm-settings" onSubmit={savePatientLlmSettings}>
                        <div className="llm-settings-copy">
                            <h3>AI summary settings</h3>
                            <p>Structured monitoring stays deterministic. An LLM can only help phrase the summary, and only when this patient has consented.</p>
                            <label className="check-label llm-consent">
                                <input type="checkbox" checked={patientLlmConsent} onChange={(event) => setPatientLlmConsent(event.target.checked)} />
                                Allow LLM-generated summaries for this patient
                            </label>
                        </div>
                        <div className="llm-controls">
                            <label>Provider
                                <select value={llmProvider} onChange={(event) => {
                                    const provider = event.target.value;
                                    setLlmProvider(provider);
                                    setLlmModel(provider === "gemini" ? "gemini-2.0-flash" : provider === "server" ? "" : "gpt-4o-mini");
                                    setLlmApiKey("");
                                    setLlmSessionConfig(null);
                                }}>
                                    <option value="server">Use server configuration</option>
                                    <option value="openai">OpenAI</option>
                                    <option value="gemini">Google Gemini</option>
                                </select>
                            </label>
                            {llmProvider !== "server" && <>
                                <label>Model<input value={llmModel} onChange={(event) => { setLlmModel(event.target.value); setLlmSessionConfig(null); }} maxLength="100" /></label>
                                <label>Provider API key
                                    <span className="secret-input">
                                        <input
                                            autoComplete="off"
                                            type={showApiKey ? "text" : "password"}
                                            value={llmApiKey}
                                            onChange={(event) => { setLlmApiKey(event.target.value); setLlmSessionConfig(null); }}
                                            placeholder="Paste your provider key"
                                            maxLength="4096"
                                        />
                                        <button className="secondary reveal-key" type="button" onClick={() => setShowApiKey(!showApiKey)}>{showApiKey ? "Hide" : "Show"}</button>
                                    </span>
                                </label>
                            </>}
                            <p className="credential-note">Keys stay in browser memory, are sent only with analysis requests, and are not saved to the patient record. Use HTTPS outside local development.</p>
                            <button type="submit" disabled={Boolean(busy)}>{busy === "llm" ? "Saving…" : "Save patient settings"}</button>
                        </div>
                    </form>
                </section>}

                <section className="data-grid">
                    <section className="data-panel"><h2>Latest biomarkers</h2><Biomarkers snapshot={data.biomarkers} /></section>
                    <section className="data-panel"><h2>Today's summary</h2><DailySummary summary={data.daily} /></section>
                    <section className="data-panel"><h2>Recent events</h2><Events events={data.events} /></section>
                    <section className="data-panel"><h2>Timeline</h2><Timeline timeline={data.timeline} /></section>
                </section>

                <section className="card transcript-panel">
                    <div><p className="eyebrow">Analysis</p><h2>Analyze a transcript</h2></div>
                    <form onSubmit={analyzeTranscript}>
                        <label>Transcript<textarea rows="4" value={transcript} onChange={(event) => setTranscript(event.target.value)} placeholder="Good morning, I am feeling okay today." /></label>
                        <button type="submit" disabled={Boolean(busy)}>{busy === "analyze" ? "Analyzing…" : "Analyze"}</button>
                    </form>
                    {analysisResult && <pre className="result-box">{JSON.stringify(analysisResult, null, 2)}</pre>}
                </section>
            </main>
            <footer>API: <code>{API_BASE || window.location.origin}</code></footer>
        </>
    );
}

function Biomarkers({ snapshot }) {
    if (!snapshot?.values?.length) return <Empty>No biomarkers recorded yet.</Empty>;
    const values = snapshot.values.filter((value) => value.available);
    return <>
        <div className="table-scroll"><table><thead><tr><th>Metric</th><th>Value</th><th>Unit</th></tr></thead><tbody>
            {values.map((value) => <tr key={value.name}><td>{value.name}</td><td>{Number.isFinite(Number(value.value)) ? Number(value.value).toFixed(3) : "-"}</td><td>{value.unit || ""}</td></tr>)}
            {!values.length && <tr><td className="muted" colSpan="3">None available yet.</td></tr>}
        </tbody></table></div>
        <p className="muted">As of {formatDate(snapshot.timestamp)}</p>
    </>;
}

function DailySummary({ summary }) {
    if (!summary) return <Empty>No summary yet.</Empty>;
    return <>
        {summary.observations?.length ? <ul>{summary.observations.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul> : <Empty>No notable deviations observed today.</Empty>}
        {summary.context_notes?.length > 0 && <ul>{summary.context_notes.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>}
        {summary.suggested_actions?.length > 0 && <><h3>Suggested actions</h3><ul>{summary.suggested_actions.map((action) => <li key={action.id || action.message}>{action.message}</li>)}</ul></>}
        <p className="muted"><em>{summary.disclaimer}</em></p>
    </>;
}

function Events({ events }) {
    if (!events?.length) return <Empty>No deviation events recorded yet.</Empty>;
    return events.slice(0, 15).map((event, index) => <article className={`event-item ${event.severity}`} key={`${event.type}-${event.timestamp}-${index}`}>
        <div className="event-heading"><strong>{event.type}</strong><span className={`badge ${event.severity}`}>{event.severity}</span></div>
        <p className="muted">{formatDate(event.timestamp)}</p>
        {event.evidence?.length > 0 && <ul>{event.evidence.map((item, evidenceIndex) => <li key={`${item.description}-${evidenceIndex}`}>{item.description}</li>)}</ul>}
    </article>);
}

function Timeline({ timeline }) {
    if (!timeline?.entries?.length) return <Empty>Nothing on the timeline yet.</Empty>;
    return [...timeline.entries].slice(-15).reverse().map((entry, index) => <article className="timeline-item" key={`${entry.timestamp}-${index}`}>
        <strong>{entry.summary}</strong><p className="muted">{formatDate(entry.timestamp)}</p>
    </article>);
}

export default function App() {
    const [token, setToken] = useState(() => window.sessionStorage.getItem(TOKEN_STORAGE_KEY));
    const [user, setUser] = useState(null);
    const [checkingSession, setCheckingSession] = useState(Boolean(token));

    useEffect(() => {
        if (!token) {
            setCheckingSession(false);
            return;
        }
        let cancelled = false;
        apiFetch("/auth/me", {}, token)
            .then((currentUser) => { if (!cancelled) setUser(currentUser); })
            .catch(() => {
                window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
                if (!cancelled) { setToken(null); setUser(null); }
            })
            .finally(() => { if (!cancelled) setCheckingSession(false); });
        return () => { cancelled = true; };
    }, [token]);

    function acceptSession(session) {
        window.sessionStorage.setItem(TOKEN_STORAGE_KEY, session.access_token);
        setToken(session.access_token);
        setUser(session.user);
        setCheckingSession(false);
    }

    async function signOut() {
        try { await apiFetch("/auth/logout", { method: "POST" }, token); } catch (_error) { /* Clear local access even if the server is unreachable. */ }
        window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
        setToken(null);
        setUser(null);
    }

    if (checkingSession) return <main className="loading-screen"><p>Checking session…</p></main>;
    if (!token || !user) return <AuthPanel onAuthenticated={acceptSession} />;
    return <AuthenticatedDashboard token={token} user={user} onSignOut={signOut} />;
}