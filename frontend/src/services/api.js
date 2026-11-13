// Typed-ish client for every HTTP endpoint the app uses.
// All transport concerns live in services/http.js; this file only names routes.

import * as http from "./http";

export const getState = () => http.get("/api/state");
export const getSettings = () => http.get("/api/settings");
export const postSettings = (change) => http.post("/api/settings", change ?? {});
export const resetSettings = () => http.post("/api/settings/reset");
export const getDevices = () => http.get("/api/devices");
export const getSamples = () => http.get("/api/samples");
export const replaySample = (name, segment) => http.post("/api/replay", { name, segment });
export const setPaused = (paused) => http.post("/api/pause", { paused });
export const clearTranscript = () => http.post("/api/clear");

export const getTtsVoices = () => http.get("/api/tts/voices");
export const synthesizeSpeech = (text, voice) =>
  http.requestAudio("/api/tts", { body: { text, voice: voice || null } });

export const uploadSample = (file) => {
  const form = new FormData();
  form.append("file", file);
  return http.requestForm("/api/samples", { form });
};

// ---------------------------------------------------------------- Q&A (P3)
export const askQuestion = (question, { sessionId = null, source = "voice" } = {}) =>
  http.post("/api/v1/qa/ask", {
    question,
    session_id: sessionId || null,
    source,
  });

export const detectQuestion = (text, parts = null) =>
  http.post("/api/v1/qa/detect", parts ? { parts } : { text });

export const getUnanswered = (limit = 50) =>
  http.get(`/api/v1/qa/unanswered?limit=${limit}`);

export const getSessions = (limit = 50, offset = 0) =>
  http.get(`/api/v1/sessions?limit=${limit}&offset=${offset}`);

export const getSession = (sessionId) =>
  http.get(`/api/v1/sessions/${encodeURIComponent(sessionId)}`);

export const deleteSession = (sessionId) =>
  http.del(`/api/v1/sessions/${encodeURIComponent(sessionId)}`);
