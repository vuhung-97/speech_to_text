// Single source of truth for text-to-speech constants shared by the drawer,
// the answer reader and the FAQ admin screen.
//
// The server reports its own limits (`max_chars`, `max_words`); the fallbacks
// below only apply until that first response arrives.

export const VOICE_STORAGE_KEY = "tts.voice";

export const FALLBACK_MAX_CHARS = 1_000;
export const FALLBACK_MAX_WORDS = 2_000;

export function readVoice() {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(VOICE_STORAGE_KEY) || "";
}

export function saveVoice(voice) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(VOICE_STORAGE_KEY, voice);
}
