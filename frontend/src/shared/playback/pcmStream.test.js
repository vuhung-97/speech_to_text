import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../services/errors";
import { streamSpeech, ttsWavUrl } from "./pcmStream";

function pcmResponse(chunks, headers = {}) {
  const body = new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(chunk));
      controller.close();
    },
  });
  return new Response(body, {
    status: 200,
    headers: {
      "Content-Type": "audio/L16",
      "X-Sample-Rate": "48000",
      "X-Tts-Session": "abc",
      "X-Estimated-Seconds": "2.5",
      ...headers,
    },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("streamSpeech", () => {
  it("re-frames a chunk that splits a sample in half", async () => {
    const samples = new Int16Array([0, 16384, -16384, 32767]);
    const bytes = new Uint8Array(samples.buffer);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(pcmResponse([bytes.slice(0, 3), bytes.slice(3)])),
    );

    const blocks = [];
    let started = null;
    let done = null;
    await streamSpeech("xin chào", "Mai", {
      onStart: (info) => {
        started = info;
      },
      onBlock: (block) => blocks.push(block),
      onDone: (info) => {
        done = info;
      },
    });

    const merged = blocks.flatMap((block) => Array.from(block));
    expect(merged).toHaveLength(4);
    expect(merged[1]).toBeCloseTo(0.5, 4);
    expect(merged[2]).toBeCloseTo(-0.5, 4);
    expect(started.sampleRate).toBe(48_000);
    expect(started.sessionId).toBe("abc");
    expect(done.seconds).toBeCloseTo(8 / 2 / 48_000, 6);
  });

  it("carries the server error message on a non-2xx response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: "đang bận" }), {
          status: 409,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(streamSpeech("x")).rejects.toMatchObject({
      name: "ApiError",
      status: 409,
      message: "đang bận",
    });
  });

  it("maps a network failure to the offline ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("failed")));

    await expect(streamSpeech("x")).rejects.toBeInstanceOf(ApiError);
  });

  it("encodes the session id in the download URL", () => {
    expect(ttsWavUrl("a b/c")).toBe("/api/v1/tts/sessions/a%20b%2Fc.wav");
  });
});
