/**
 * TheraVoice dashboard.
 *
 * A deliberately dependency-free, vanilla-JS single page app served by the
 * FastAPI backend itself (mounted at /dashboard -- see api/app.py). Talks to
 * the same-origin REST API by default; pass ?api=http://host:port to point
 * it at a different backend instance.
 */

const params = new URLSearchParams(window.location.search);
const API_BASE = params.get("api") || "";

const el = (id) => document.getElementById(id);
document.addEventListener("DOMContentLoaded", () => {
  el("api-base-display").textContent = API_BASE || window.location.origin;

  const savedPatientId = window.localStorage.getItem("theravoice.lastPatientId");
  if (savedPatientId) {
    el("patient-id").value = savedPatientId;
  }

  el("load-btn").addEventListener("click", () => loadPatientData());
  el("sync-btn").addEventListener("click", () => syncFromBee());
  el("analyze-btn").addEventListener("click", () => analyzeTranscript());
});

function currentPatientId() {
  const value = el("patient-id").value.trim();
  if (value) {
    window.localStorage.setItem("theravoice.lastPatientId", value);
  }
  return value;
}

function setStatus(message, isError = false) {
  const line = el("status-line");
  line.textContent = message;
  line.style.color = isError ? "var(--danger)" : "var(--muted)";
}

async function apiFetch(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  let body = null;
  try {
    body = await response.json();
  } catch (_err) {
    body = null;
  }
  if (!response.ok) {
    const detail = body && body.detail ? body.detail : response.statusText;
    throw new Error(detail);
  }
  return body;
}

function badge(status) {
  return `<span class="badge ${status}">${status}</span>`;
}

function renderBiomarkers(snapshot) {
  const container = el("biomarkers-table");
  if (!snapshot || !snapshot.values || snapshot.values.length === 0) {
    container.innerHTML = '<p class="muted">No biomarkers recorded yet.</p>';
    return;
  }
  const rows = snapshot.values
    .filter((v) => v.available)
    .map(
      (v) =>
        `<tr><td>${v.name}</td><td>${Number(v.value).toFixed(3)}</td><td>${v.unit || ""}</td></tr>`
    )
    .join("");
  container.innerHTML = `
    <table>
      <thead><tr><th>Metric</th><th>Value</th><th>Unit</th></tr></thead>
      <tbody>${rows || '<tr><td colspan="3" class="muted">None available yet.</td></tr>'}</tbody>
    </table>
    <p class="muted">As of ${new Date(snapshot.timestamp).toLocaleString()}</p>
  `;
}

function renderDailySummary(summary) {
  const container = el("daily-summary");
  if (!summary) {
    container.innerHTML = '<p class="muted">No summary yet.</p>';
    return;
  }
  const observations = summary.observations && summary.observations.length
    ? `<ul>${summary.observations.map((o) => `<li>${o}</li>`).join("")}</ul>`
    : '<p class="muted">No notable deviations observed today.</p>';
  const context = summary.context_notes && summary.context_notes.length
    ? `<ul>${summary.context_notes.map((n) => `<li>${n}</li>`).join("")}</ul>`
    : "";
  container.innerHTML = `
    ${observations}
    ${context}
    <p class="muted"><em>${summary.disclaimer}</em></p>
  `;
}

function renderEvents(events) {
  const container = el("events-list");
  if (!events || events.length === 0) {
    container.innerHTML = '<p class="muted">No deviation events recorded yet.</p>';
    return;
  }
  container.innerHTML = events
    .slice(0, 15)
    .map((e) => {
      const evidence = (e.evidence || []).map((ev) => `<li>${ev.description}</li>`).join("");
      return `
        <div class="event-item ${e.severity}">
          <strong>${e.type}</strong> ${badge(e.severity)}
          <div class="muted">${new Date(e.timestamp).toLocaleString()}</div>
          <ul>${evidence}</ul>
        </div>`;
    })
    .join("");
}

function renderTimeline(timeline) {
  const container = el("timeline-list");
  if (!timeline || !timeline.entries || timeline.entries.length === 0) {
    container.innerHTML = '<p class="muted">Nothing on the timeline yet.</p>';
    return;
  }
  container.innerHTML = timeline.entries
    .slice(-15)
    .reverse()
    .map(
      (entry) =>
        `<div class="timeline-item"><strong>${entry.summary}</strong><div class="muted">${new Date(entry.timestamp).toLocaleString()}</div></div>`
    )
    .join("");
}

async function loadPatientData() {
  const patientId = currentPatientId();
  if (!patientId) {
    setStatus("Enter a patient ID first.", true);
    return;
  }
  setStatus("Loading…");
  try {
    await apiFetch(`/patients/${encodeURIComponent(patientId)}`);

    const [latest, daily, events, timeline] = await Promise.all([
      apiFetch(`/patients/${encodeURIComponent(patientId)}/biomarkers/latest`).catch(() => null),
      apiFetch(`/patients/${encodeURIComponent(patientId)}/reports/daily`).catch(() => null),
      apiFetch(`/patients/${encodeURIComponent(patientId)}/events`).catch(() => []),
      apiFetch(`/patients/${encodeURIComponent(patientId)}/reports/timeline`).catch(() => null),
    ]);

    renderBiomarkers(latest);
    renderDailySummary(daily);
    renderEvents(events);
    renderTimeline(timeline);
    setStatus(`Loaded ${patientId}.`);
  } catch (err) {
    setStatus(`Could not load patient: ${err.message}`, true);
  }
}

async function syncFromBee() {
  const patientId = currentPatientId();
  if (!patientId) {
    setStatus("Enter a patient ID first.", true);
    return;
  }
  setStatus("Syncing from Bee…");
  el("sync-btn").disabled = true;
  try {
    const result = await apiFetch(`/patients/${encodeURIComponent(patientId)}/bee/sync`, {
      method: "POST",
    });
    setStatus(result.message);
    await loadPatientData();
  } catch (err) {
    setStatus(`Bee sync failed: ${err.message}`, true);
  } finally {
    el("sync-btn").disabled = false;
  }
}

async function analyzeTranscript() {
  const patientId = currentPatientId();
  const text = el("transcript-input").value.trim();
  if (!patientId || !text) {
    setStatus("Enter both a patient ID and some text to analyze.", true);
    return;
  }
  el("analyze-btn").disabled = true;
  try {
    const result = await apiFetch(`/ingestion/transcript`, {
      method: "POST",
      body: JSON.stringify({ patient_id: patientId, text }),
    });
    el("analyze-result").textContent = JSON.stringify(result, null, 2);
    await loadPatientData();
  } catch (err) {
    el("analyze-result").textContent = `Error: ${err.message}`;
  } finally {
    el("analyze-btn").disabled = false;
  }
}
