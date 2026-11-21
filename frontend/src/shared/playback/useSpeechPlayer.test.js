import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useSpeechPlayer } from "./useSpeechPlayer";

const players = [];
const playback = vi.hoisted(() => ({ resumeImpl: () => Promise.resolve(undefined) }));

vi.mock("./pcmPlayer", () => ({
  PcmPlayer: vi.fn(function PcmPlayer(options = {}) {
    const instance = {
      options,
      resume: vi.fn(() => playback.resumeImpl()),
      setSampleRate: vi.fn(),
      push: vi.fn().mockResolvedValue(undefined),
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
  playback.resumeImpl = () => Promise.resolve(undefined);
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

  it("keeps the claim after the last byte so a new read stops the tail", async () => {
    vi.mocked(streamSpeech).mockImplementation((text, voice, handlers) => {
      handlers.onStart({ sampleRate: 48000, estimated: 20, sessionId: "s1" });
      handlers.onBlock(new Float32Array(16));
      handlers.onDone({ sessionId: "s1" });
      return Promise.resolve({ sessionId: "s1" });
    });
    const { result } = renderHook(() => useSpeechPlayer());

    await act(async () => {
      await result.current.start("câu một", "Mai");
    });
    // The whole answer was received, but the client buffer is still playing.
    expect(result.current.status).toBe("playing");

    await act(async () => {
      await result.current.start("câu hai", "Mai");
    });

    expect(players[0].stop).toHaveBeenCalled();
    expect(players[1].stop).not.toHaveBeenCalled();
  });

  it("reports done when the buffer actually drains", async () => {
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
    expect(result.current.status).toBe("playing");

    await act(async () => {
      players[0].options.onDrained();
    });

    expect(players[0].stop).toHaveBeenCalled();
    expect(result.current.status).toBe("done");
    expect(result.current.sessionId).toBe("s1");
    expect(result.current.downloadUrl).toBe("/wav/s1");
  });

  it("does not start a stream after unmount while resume() is pending", async () => {
    let resolveResume;
    playback.resumeImpl = () =>
      new Promise((resolve) => {
        resolveResume = resolve;
      });
    const { result, unmount } = renderHook(() => useSpeechPlayer());

    let pending;
    act(() => {
      pending = result.current.start("câu", "Mai");
    });
    unmount();

    await act(async () => {
      resolveResume();
      await pending;
    });

    expect(streamSpeech).not.toHaveBeenCalled();
  });
});
