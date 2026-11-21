import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "./errors";
import { request, requestAudio, requestForm, requestStream } from "./http";

function jsonResponse(body, { status = 200 } = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("request", () => {
  it("returns the parsed JSON payload", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ ok: true, value: 1 })));

    await expect(request("/api/x")).resolves.toEqual({ ok: true, value: 1 });
  });

  it("maps a non-2xx response to ApiError with the server message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ ok: false, error: "không tìm thấy" }, { status: 404 })),
    );

    await expect(request("/api/x")).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      message: "không tìm thấy",
    });
  });

  it("treats ok:false in a 200 response as a failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ ok: false, error: "hỏng" })));

    await expect(request("/api/x")).rejects.toBeInstanceOf(ApiError);
  });

  it("maps a network failure to the offline ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("failed to fetch")));

    await expect(request("/api/x")).rejects.toMatchObject({ status: 0, code: "network" });
  });

  it("aborts a request that exceeds its timeout", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((_url, init) => new Promise((_resolve, reject) => {
        init.signal.addEventListener("abort", () => {
          reject(new DOMException("aborted", "AbortError"));
        });
      })),
    );

    await expect(request("/api/slow", { timeout: 10 })).rejects.toMatchObject({
      code: "aborted",
    });
  });
});

describe("requestForm", () => {
  it("lets the browser set the multipart boundary", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await requestForm("/api/upload", { form: new FormData() });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers["Content-Type"]).toBeUndefined();
  });
});

describe("requestStream", () => {
  it("returns the raw response so callers can read the body", async () => {
    const response = new Response("pcm", {
      status: 200,
      headers: { "Content-Type": "audio/L16" },
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));

    const result = await requestStream("/api/v1/tts/stream", { body: { text: "x" } });

    await expect(result.text()).resolves.toBe("pcm");
  });

  it("normalises a non-2xx response to ApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ ok: false, error: "đang bận" }, { status: 409 })),
    );

    await expect(requestStream("/api/v1/tts/stream", { body: {} })).rejects.toMatchObject({
      name: "ApiError",
      status: 409,
      message: "đang bận",
    });
  });
});

describe("requestAudio", () => {
  it("rejects a response that is not audio", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ ok: true })));

    await expect(requestAudio("/api/tts")).rejects.toMatchObject({ code: "bad-content-type" });
  });

  it("returns the blob and the reported duration", async () => {
    const response = new Response("pcm", {
      status: 200,
      headers: { "Content-Type": "audio/wav", "X-Audio-Seconds": "1.5" },
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));

    const result = await requestAudio("/api/tts");

    expect(await result.blob.text()).toBe("pcm");
    expect(result.seconds).toBe(1.5);
  });
});
