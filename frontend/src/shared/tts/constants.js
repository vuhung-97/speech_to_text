// Single source of truth for the selected reading voice and speed (localStorage).

export const VOICE_STORAGE_KEY = "tts.voice";
export const SPEED_STORAGE_KEY = "tts.speed";

export const MIN_SPEED = 0.8;
export const MAX_SPEED = 2;
export const SPEED_STEP = 0.2;
export const DEFAULT_SPEED = 1;

export function readVoice() {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(VOICE_STORAGE_KEY) || "";
}

export function saveVoice(voice) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(VOICE_STORAGE_KEY, voice);
}

export function clampSpeed(value) {
  if (value === null || value === undefined || value === "") return DEFAULT_SPEED;
  const number = Number(value);
  if (!Number.isFinite(number)) return DEFAULT_SPEED;
  const clamped = Math.min(MAX_SPEED, Math.max(MIN_SPEED, number));
  return Number((Math.round(clamped / SPEED_STEP) * SPEED_STEP).toFixed(1));
}

export function readSpeed() {
  if (typeof window === "undefined") return DEFAULT_SPEED;
  return clampSpeed(window.localStorage.getItem(SPEED_STORAGE_KEY));
}

export function saveSpeed(speed) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(SPEED_STORAGE_KEY, String(clampSpeed(speed)));
}
