// Single source of truth for the reading voice, speed and playback buffer.

export const VOICE_STORAGE_KEY = "tts.voice";
export const SPEED_STORAGE_KEY = "tts.speed";
export const PREBUFFER_STORAGE_KEY = "tts.prebuffer";
export const LOOKAHEAD_STORAGE_KEY = "tts.lookahead";

export const MIN_SPEED = 0.8;
export const MAX_SPEED = 2;
export const SPEED_STEP = 0.2;
export const DEFAULT_SPEED = 1;

export const MIN_PREBUFFER = 0.5;
export const MAX_PREBUFFER = 8;
export const PREBUFFER_STEP = 0.5;
export const DEFAULT_PREBUFFER = 2.5;

export const MIN_LOOKAHEAD = 2;
export const MAX_LOOKAHEAD = 10;
export const LOOKAHEAD_STEP = 1;
export const DEFAULT_LOOKAHEAD = 4;

const SPEED = {
  min: MIN_SPEED,
  max: MAX_SPEED,
  step: SPEED_STEP,
  fallback: DEFAULT_SPEED,
  decimals: 1,
};
const PREBUFFER = {
  min: MIN_PREBUFFER,
  max: MAX_PREBUFFER,
  step: PREBUFFER_STEP,
  fallback: DEFAULT_PREBUFFER,
};
const LOOKAHEAD = {
  min: MIN_LOOKAHEAD,
  max: MAX_LOOKAHEAD,
  step: LOOKAHEAD_STEP,
  fallback: DEFAULT_LOOKAHEAD,
};

const hasStorage = () => typeof window !== "undefined";

function readStored(key, fallback = "") {
  if (!hasStorage()) return fallback;
  return window.localStorage.getItem(key) ?? fallback;
}

function writeStored(key, value) {
  if (!hasStorage()) return;
  window.localStorage.setItem(key, String(value));
}

// One rounding rule for every numeric preference (speed, prebuffer, lookahead).
function snap(value, { min, max, step, fallback, decimals = 2 }) {
  if (value === null || value === undefined || value === "") return fallback;
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  const clamped = Math.min(max, Math.max(min, number));
  return Number((Math.round(clamped / step) * step).toFixed(decimals));
}

export const clampSpeed = (value) => snap(value, SPEED);
export const readSpeed = () => clampSpeed(readStored(SPEED_STORAGE_KEY));
export const saveSpeed = (speed) => writeStored(SPEED_STORAGE_KEY, clampSpeed(speed));

export const clampPrebuffer = (value) => snap(value, PREBUFFER);
export const readPrebuffer = () => clampPrebuffer(readStored(PREBUFFER_STORAGE_KEY));
export function savePrebuffer(value) {
  const next = clampPrebuffer(value);
  writeStored(PREBUFFER_STORAGE_KEY, next);
  return next;
}

export const clampLookahead = (value) => snap(value, LOOKAHEAD);
export const readLookahead = () => clampLookahead(readStored(LOOKAHEAD_STORAGE_KEY));
export function saveLookahead(value) {
  const next = clampLookahead(value);
  writeStored(LOOKAHEAD_STORAGE_KEY, next);
  return next;
}

export const readVoice = () => readStored(VOICE_STORAGE_KEY);
export const saveVoice = (voice) => writeStored(VOICE_STORAGE_KEY, voice);
