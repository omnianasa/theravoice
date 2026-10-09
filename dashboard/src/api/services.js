import { api } from "./client.js";
import { endpoints } from "./endpoints.js";

export const authService = {
  register: (payload) => api.post(endpoints.register, payload),
  login: (payload) => api.post(endpoints.login, payload),
  me: () => api.get(endpoints.me),
  logout: () => api.post(endpoints.logout),
};

export const patientService = {
  create: (payload) => api.post(endpoints.patients, payload),
  get: (patientId, options) => api.get(endpoints.patient(patientId), options),
  updateLlmConsent: (patientId, allowed) =>
    api.patch(endpoints.patientConsent(patientId), { consent_llm_processing: allowed }),
};

export const analysisService = {
  transcript: (patientId, text, options) =>
    api.post(endpoints.analyzeTranscript, { patient_id: patientId, text }, options),
  audio: (patientId, file, text, options) => {
    const body = new FormData();
    body.set("patient_id", patientId);
    body.set("file", file, file.name);
    if (text.trim()) body.set("text", text);
    return api.post(endpoints.analyzeAudio, body, options);
  },
};

export const monitoringService = {
  health: (options) => api.get(endpoints.health, options),
  info: (options) => api.get(endpoints.info, options),
  integrations: (options) => api.get(endpoints.integrations, options),
  biomarkers: (patientId, options) => api.get(endpoints.biomarkers(patientId), options),
  latestBiomarkers: (patientId, options) => api.get(endpoints.latestBiomarkers(patientId), options),
  events: (patientId, options) => api.get(endpoints.events(patientId), options),
  daily: (patientId, day, options) => {
    const query = day ? `?day=${encodeURIComponent(day)}` : "";
    return api.get(`${endpoints.dailyReport(patientId)}${query}`, options);
  },
  timeline: (patientId, options) => api.get(endpoints.timelineReport(patientId), options),
  clinical: (patientId, options) => api.get(endpoints.clinicalReport(patientId), options),
};

export const integrationService = {
  beeStatus: (patientId, options) => api.get(endpoints.beeStatus(patientId), options),
  beeSync: (patientId, options) => api.post(endpoints.beeSync(patientId), undefined, options),
};

export const careService = {
  schedules: (patientId, options) => api.get(endpoints.schedules(patientId), options),
  medicationEvents: (patientId, options) => api.get(endpoints.medicationEvents(patientId), options),
  exercises: (patientId, options) => api.get(endpoints.exercises(patientId), options),
  recommendations: (patientId, options) => api.get(endpoints.recommendations(patientId), options),
  sessions: (patientId, options) => api.get(endpoints.therapySessions(patientId), options),
  startSession: (patientId, exerciseId, options) =>
    api.post(`${endpoints.therapySessions(patientId)}?exercise_id=${encodeURIComponent(exerciseId)}`, undefined, options),
};
