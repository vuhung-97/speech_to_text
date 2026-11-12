const request = async (url, options = {}) => {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
};

const json = (body) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body ?? {}),
});

export const getState = () => request("/api/state");
export const getSettings = () => request("/api/settings");
export const postSettings = (patch) => request("/api/settings", json(patch));
export const resetSettings = () => request("/api/settings/reset", { method: "POST" });
export const getDevices = () => request("/api/devices");
export const getSamples = () => request("/api/samples");
export const replaySample = (name, segment) =>
  request("/api/replay", json({ name, segment }));
export const setPaused = (paused) => request("/api/pause", json({ paused }));
export const clearTranscript = () => request("/api/clear", { method: "POST" });

export const uploadSample = (file) => {
  const form = new FormData();
  form.append("file", file);
  return request("/api/samples", { method: "POST", body: form });
};
