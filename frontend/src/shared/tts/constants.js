// Single source of truth for the selected reading voice (localStorage).

export const VOICE_STORAGE_KEY = "tts.voice";

export function readVoice() {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(VOICE_STORAGE_KEY) || "";
}

export function saveVoice(voice) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(VOICE_STORAGE_KEY, voice);
}
