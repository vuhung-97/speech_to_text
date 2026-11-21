import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useSpeechPlayer } from "./useSpeechPlayer";

const players = [];

vi.mock("./pcmPlayer", () => ({
  PcmPlayer: vi.fn(function PcmPlayer() {
    const instance = {
      resume: vi.fn().mockResolvedValue(undefined),
      setSampleRate: vi.fn(),
      push: vi.fn(),
      flush: vi.fn(),
      stop: vi.fn(),
    };
    players.push(instance);
    return instance;
  }),
}));

const streamCalls = [];
vi.mock("./pcmStream", () => ({
  streamSpeech: vi.fn((text, voice, handlers) => {
    streamCalls.push({ text, voice, handlers });
    return Promise.resolve({ sessionId: "" });
  }),
  ttsWavUrl: (id) => `/wav/${id}`,
}));

import { streamSpeech } from "./pcmStream";

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(streamSpeech).mockReset();
  vi.mocked(streamSpeech).mockImplementation((text, voice, handlers) => {
    streamCalls.push({ text, voice, handlers });
    return Promise.resolve({ sessionId: "" });
  });
  players.length = 0;
  streamCalls.length = 0;
});

describe("useSpeechPlayer", () => {
  it("a second start aborts the first stream and hands over the channel", async () => {
    const { result } = renderHook(() => useSpeechPlayer());

    await act(async () => {
      result.current.start("câu một", "Mai");
    });
    await act(async () => {
      result.current.start("câu hai", "Mai");
    });

    // Both requests were opened; the first was aborted when the second claimed.
    expect(streamCalls).toHaveLength(2);
    expect(streamCalls[0].handlers.signal.aborted).toBe(true);
    expect(streamCalls[1].text).toBe("câu hai");
    expect(players).toHaveLength(2);
    expect(players[0].stop).toHaveBeenCalled();
  });

  it("stop while loading aborts the request and drops late blocks", async () => {
    let resolvePending;
    let pendingHandlers;
    vi.mocked(streamSpeech).mockImplementationOnce((text, voice, handlers) => {
      pendingHandlers = handlers;
      return new Promise((resolve) => {
        resolvePending = resolve;
      });
    });
    const { result } = renderHook(() => useSpeechPlayer());

    let startPromise;
    act(() => {
      startPromise = result.current.start("câu dài", "Mai");
    });
    await act(async () => {
      await Promise.resolve();
    });
    expect(pendingHandlers).toBeDefined();

    await act(async () => {
      result.current.stop();
    });

    expect(pendingHandlers.signal.aborted).toBe(true);
    expect(result.current.status).toBe("idle");

    pendingHandlers.onBlock(new Float32Array(160));
    expect(players[0].push).not.toHaveBeenCalled();

    await act(async () => {
      resolvePending({ sessionId: "s1" });
      await startPromise;
    });
  });

  it("reports done and frees the channel when the stream ends", async () => {
    vi.mocked(streamSpeech).mockImplementationOnce((text, voice, handlers) => {
      handlers.onStart({ sampleRate: 48000, estimated: 2, sessionId: "s1" });
      handlers.onBlock(new Float32Array(16));
      handlers.onDone({ sessionId: "s1" });
      return Promise.resolve({ sessionId: "s1" });
    });
    const { result } = renderHook(() => useSpeechPlayer());

    await act(async () => {
      await result.current.start("ngắn", "Mai");
    });

    expect(result.current.status).toBe("done");
    expect(result.current.sessionId).toBe("s1");
    expect(result.current.downloadUrl).toBe("/wav/s1");
  });
});
