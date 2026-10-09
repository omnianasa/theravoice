const patientPath = (patientId) => `/patients/${encodeURIComponent(patientId)}`;

export const endpoints = Object.freeze({
  register: "/auth/register",
  login: "/auth/login",
  me: "/auth/me",
  logout: "/auth/logout",
  health: "/health",
  info: "/info",
  integrations: "/integrations",
  patients: "/patients",
  patient: patientPath,
  patientConsent: (patientId) => `${patientPath(patientId)}/consent`,
  analyzeTranscript: "/analyses/transcript",
  analyzeAudio: "/analyses/audio",
  biomarkers: (patientId) => `${patientPath(patientId)}/biomarkers`,
  latestBiomarkers: (patientId) => `${patientPath(patientId)}/biomarkers/latest`,
  events: (patientId) => `${patientPath(patientId)}/events`,
  dailyReport: (patientId) => `${patientPath(patientId)}/reports/daily`,
  timelineReport: (patientId) => `${patientPath(patientId)}/reports/timeline`,
  clinicalReport: (patientId) => `${patientPath(patientId)}/reports/clinical`,
  beeStatus: (patientId) => `${patientPath(patientId)}/integrations/bee/status`,
  beeSync: (patientId) => `${patientPath(patientId)}/integrations/bee/sync`,
  schedules: (patientId) => `${patientPath(patientId)}/medications/schedules`,
  medicationEvents: (patientId) => `${patientPath(patientId)}/medications/events`,
  exercises: (patientId) => `${patientPath(patientId)}/therapy/exercises`,
  recommendations: (patientId) => `${patientPath(patientId)}/therapy/recommendations`,
  therapySessions: (patientId) => `${patientPath(patientId)}/therapy/sessions`,
});

export function apiPath(endpoint) {
  return `/api/v1${endpoint}`;
}
