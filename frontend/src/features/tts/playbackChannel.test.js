import { describe, expect, it, vi } from "vitest";

import {
  beginPlayback,
  endPlayback,
  isCurrentPlayback,
  stopAllPlayback,
} from "./playbackChannel";

describe("playbackChannel", () => {
  it("claiming a new source stops the previous one", () => {
    const first = vi.fn();
    const key1 = beginPlayback(first);
    expect(isCurrentPlayback(key1)).toBe(true);

    const second = vi.fn();
    const key2 = beginPlayback(second);

    expect(first).toHaveBeenCalledTimes(1);
    expect(isCurrentPlayback(key1)).toBe(false);
    expect(isCurrentPlayback(key2)).toBe(true);
  });

  it("an old owner cannot end a newer claim", () => {
    beginPlayback(vi.fn());
    const key2 = beginPlayback(vi.fn());

    endPlayback(1); // stale key
    expect(isCurrentPlayback(key2)).toBe(true);
  });

  it("stopAllPlayback silences the owner exactly once", () => {
    const stop = vi.fn();
    beginPlayback(stop);

    stopAllPlayback();
    stopAllPlayback();

    expect(stop).toHaveBeenCalledTimes(1);
  });

  it("releasing the current owner leaves the channel free", () => {
    const key = beginPlayback(vi.fn());
    endPlayback(key);
    expect(isCurrentPlayback(key)).toBe(false);
  });
});
