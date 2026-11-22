import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_SPEED,
  SPEED_STORAGE_KEY,
  VOICE_STORAGE_KEY,
  clampSpeed,
  readSpeed,
  readVoice,
  saveSpeed,
  saveVoice,
} from "./constants";

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

  it("defaults the reading speed to 1x", () => {
    expect(readSpeed()).toBe(DEFAULT_SPEED);
  });

  it("clamps speed to 0.8–2.0 and snaps it to 0.2 steps", () => {
    expect(clampSpeed(0.2)).toBe(0.8);
    expect(clampSpeed(9)).toBe(2);
    expect(clampSpeed(1.3)).toBe(1.4);
  });

  it("round-trips the reading speed through storage", () => {
    saveSpeed(1.4);
    expect(window.localStorage.getItem(SPEED_STORAGE_KEY)).toBe("1.4");
    expect(readSpeed()).toBe(1.4);
  });
});
