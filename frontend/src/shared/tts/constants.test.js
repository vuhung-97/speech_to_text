import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { VOICE_STORAGE_KEY, readVoice, saveVoice } from "./constants";

describe("tts constants", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns an empty voice when nothing is stored", () => {
    expect(readVoice()).toBe("");
  });

  it("round-trips a voice through the single storage key", () => {
    saveVoice("giọng-nam");
    expect(window.localStorage.getItem(VOICE_STORAGE_KEY)).toBe("giọng-nam");
    expect(readVoice()).toBe("giọng-nam");
  });
});
