// Typed-ish client for every HTTP endpoint the app uses.
// All transport concerns live in services/http.js; this file only names routes.

import * as http from "./http";

// Versioned contract prefix, shared with the streaming player.
export const API_V1 = "/api/v1";

const v1 = (path) => `${API_V1}${path}`;

const withQuery = (path, params) => {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === "" || value === null || value === undefined) continue;
    search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `${path}?${query}` : path;
};

// ------------------------------------------------------------ legacy (/api)
export const getState = () => http.get("/api/state");
export const getSettings = () => http.get("/api/settings");
export const postSettings = (change) => http.post("/api/settings", change ?? {});
export const resetSettings = () => http.post("/api/settings/reset");
export const getSamples = () => http.get("/api/samples");
export const replaySample = (name, segment) => http.post("/api/replay", { name, segment });

export const getTtsVoices = () => http.get("/api/tts/voices");
export const synthesizeSpeech = (text, voice) =>
  http.requestAudio("/api/tts", { body: { text, voice: voice || null } });

export const uploadSample = (file) => {
  const form = new FormData();
  form.append("file", file);
  return http.requestForm("/api/samples", { form });
};

// ---------------------------------------------------------------- Q&A (v1)
export const askQuestion = (
  question,
  { sessionId = null, source = "voice", documentId = null, signal } = {},
) =>
  http.post(
    v1("/qa/ask"),
    {
      question,
      session_id: sessionId || null,
      source,
      document_id: documentId || null,
    },
    { signal },
  );

export const getUnanswered = (limit = 50) =>
  http.get(withQuery(v1("/qa/unanswered"), { limit }));

export const getSessions = (limit = 50, offset = 0) =>
  http.get(withQuery(v1("/sessions"), { limit, offset }));

export const getSession = (sessionId, options = {}) =>
  http.get(v1(`/sessions/${encodeURIComponent(sessionId)}`), options);

export const deleteSession = (sessionId) =>
  http.del(v1(`/sessions/${encodeURIComponent(sessionId)}`));

// ------------------------------------------------------------ FAQ catalogue
export const getFaqEntries = ({
  q = "",
  category = "",
  active = "",
  documentId = "",
  limit = 100,
  offset = 0,
} = {}) =>
  http.get(
    withQuery(v1("/faq/entries"), {
      limit,
      offset,
      q,
      category,
      document_id: documentId,
      active,
    }),
  );

export const createFaqEntry = (entry) => http.post(v1("/faq/entries"), entry);

export const updateFaqEntry = (entryId, patch) =>
  http.patch(v1(`/faq/entries/${encodeURIComponent(entryId)}`), patch);

export const deleteFaqEntry = (entryId) =>
  http.del(v1(`/faq/entries/${encodeURIComponent(entryId)}`));

export const importFaqCsv = (file) => {
  const form = new FormData();
  form.append("file", file);
  return http.requestForm(v1("/faq/import"), { form });
};

// Outlines are parsed and embedded server-side; allow a longer timeout.
export const importFaqDocx = (file) => {
  const form = new FormData();
  form.append("file", file);
  return http.requestForm(v1("/faq/import-docx"), { form, timeout: 120_000 });
};

export const reindexFaq = () => http.post(v1("/faq/reindex"));

export const getFaqStats = () => http.get(v1("/faq/stats"));

export const getFaqDocuments = () => http.get(v1("/faq/documents"));

export const renameFaqDocument = (documentId, name) =>
  http.patch(v1(`/faq/documents/${encodeURIComponent(documentId)}`), { name });

export const deleteFaqDocument = (documentId) =>
  http.del(v1(`/faq/documents/${encodeURIComponent(documentId)}`));

export const prerenderFaq = (entryId, voice) =>
  http.post(v1(`/faq/entries/${encodeURIComponent(entryId)}/prerender`), {
    voice: voice || null,
  });

export const getPrerender = (jobId) =>
  http.get(v1(`/faq/prerender/${encodeURIComponent(jobId)}`));

export const getAnswerSpeech = (answerId, voice) =>
  http.post(v1(`/qa/answers/${encodeURIComponent(answerId)}/speech`), {
    voice: voice || null,
  });

export const getAudit = (limit = 30) => http.get(withQuery(v1("/audit"), { limit }));
