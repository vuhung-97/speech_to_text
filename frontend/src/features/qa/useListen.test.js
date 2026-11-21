import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GRACE_MS } from "../mic/constants";
import { useListen } from "./useListen";

const mockStream = {
  live: { stable: "", tentative: "" },
  lastFinal: { seq: 0, text: "" },
  level: 0,
  error: "",
  notice: "",
  state: "idle",
  packets: 0,
  deviceLabel: "",
  sampleRate: 16000,
  start: vi.fn(),
  stop: vi.fn(),
  clear: vi.fn(),
};

vi.mock("../mic/useSpeechStream", () => ({
  useSpeechStream: () => mockStream,
}));

const pushFinal = (rerender, text) =>
  act(() => {
    mockStream.lastFinal = { seq: mockStream.lastFinal.seq + 1, text };
    mockStream.live = { stable: "", tentative: "" };
    rerender();
  });

const setLive = (rerender, stable, tentative) =>
  act(() => {
    mockStream.live = { stable, tentative };
    rerender();
  });

beforeEach(() => {
  vi.useFakeTimers();
  vi.clearAllMocks();
  mockStream.live = { stable: "", tentative: "" };
  mockStream.lastFinal = { seq: 0, text: "" };
  mockStream.start.mockResolvedValue(true);
  mockStream.stop.mockResolvedValue(undefined);
  mockStream.clear.mockReturnValue(undefined);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useListen", () => {
  it("hands over each finalized sentence as soon as it arrives", async () => {
    const onText = vi.fn();
    const { result, rerender } = renderHook(() => useListen({ onText }));

    await act(async () => {
      await result.current.start();
    });
    expect(result.current.active).toBe(true);

    pushFinal(rerender, "câu một");
    expect(onText).toHaveBeenLastCalledWith("câu một");

    pushFinal(rerender, "câu hai");
    expect(onText).toHaveBeenLastCalledWith("câu hai");
    expect(onText).toHaveBeenCalledTimes(2);
  });

  it("auto-stops after GRACE_MS without new speech", async () => {
    const onText = vi.fn();
    const { result, rerender } = renderHook(() => useListen({ onText }));

    await act(async () => {
      await result.current.start();
    });
    pushFinal(rerender, "câu một"); // arms the 1.5 s grace

    await act(async () => {
      vi.advanceTimersByTime(GRACE_MS - 100);
    });
    expect(result.current.active).toBe(true);

    await act(async () => {
      vi.advanceTimersByTime(100);
    });
    expect(result.current.active).toBe(false);
    expect(mockStream.stop).toHaveBeenCalled();
  });

  it("returns only the still-spoken tail from stop, without repeating finals", async () => {
    const onText = vi.fn();
    const { result, rerender } = renderHook(() => useListen({ onText }));

    await act(async () => {
      await result.current.start();
    });
    pushFinal(rerender, "câu một");
    setLive(rerender, "", "đang nói");

    let tail = "";
    await act(async () => {
      tail = await result.current.stop();
    });

    expect(tail).toBe("đang nói");
    expect(onText).toHaveBeenCalledTimes(2);
    expect(onText).toHaveBeenLastCalledWith("đang nói");
  });

  it("ignores finals that arrive after the session ended", async () => {
    const onText = vi.fn();
    const { result, rerender } = renderHook(() => useListen({ onText }));

    await act(async () => {
      await result.current.start();
    });
    await act(async () => {
      await result.current.stop();
    });
    const calls = onText.mock.calls.length;

    pushFinal(rerender, "câu muộn");
    expect(onText).toHaveBeenCalledTimes(calls);
  });
});
