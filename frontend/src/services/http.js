// The only place allowed to call fetch. Components consume features' api.js.
//
// Responsibilities: build the request, merge abort signals, apply a timeout,
// parse JSON, and convert every failure into ApiError. Nothing else.

import { ApiError } from "./errors";

const DEFAULT_TIMEOUT = 15_000;

const JSON_HEADERS = { Accept: "application/json" };

function linkSignal(signal, controller) {
  if (!signal) return () => {};
  const forward = () => controller.abort(signal.reason);
  if (signal.aborted) forward();
  else signal.addEventListener("abort", forward, { once: true });
  return () => signal.removeEventListener("abort", forward);
}

async function readJson(response) {
  const type = response.headers.get("content-type") || "";
  if (!type.includes("json")) return null;
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function request(path, options = {}) {
  const {
    method = "GET",
    body,
    headers,
    signal,
    timeout = DEFAULT_TIMEOUT,
  } = options;

  const controller = new AbortController();
  const unlink = linkSignal(signal, controller);
  const timer = timeout
    ? window.setTimeout(() => controller.abort(new DOMException("timeout", "TimeoutError")), timeout)
    : 0;

  try {
    const response = await fetch(path, {
      method,
      headers: {
        ...JSON_HEADERS,
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
        ...headers,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
    const data = await readJson(response);
    if (!response.ok || data?.ok === false) {
      throw ApiError.fromResponse(response, data);
    }
    return data ?? {};
  } catch (error) {
    throw ApiError.fromNetwork(error);
  } finally {
    window.clearTimeout(timer);
    unlink();
  }
}

export const get = (path, options) => request(path, options);
export const post = (path, body, options) => request(path, { ...options, method: "POST", body });
export const patch = (path, body, options) => request(path, { ...options, method: "PATCH", body });
export const del = (path, options) => request(path, { ...options, method: "DELETE" });

export async function requestForm(path, options = {}) {
  const { method = "POST", form, signal, timeout = 30_000 } = options;
  const controller = new AbortController();
  const unlink = linkSignal(signal, controller);
  const timer = timeout
    ? window.setTimeout(() => controller.abort(new DOMException("timeout", "TimeoutError")), timeout)
    : 0;

  try {
    // Never set Content-Type for FormData: the browser owns the boundary.
    const response = await fetch(path, {
      method,
      headers: { Accept: "application/json" },
      body: form,
      signal: controller.signal,
    });
    const data = await readJson(response);
    if (!response.ok || data?.ok === false) {
      throw ApiError.fromResponse(response, data);
    }
    return data ?? {};
  } catch (error) {
    throw ApiError.fromNetwork(error);
  } finally {
    window.clearTimeout(timer);
    unlink();
  }
}

export async function requestAudio(path, options = {}) {
  const { method = "POST", body, signal, timeout = 0, headers } = options;
  const controller = new AbortController();
  const unlink = linkSignal(signal, controller);
  const timer = timeout
    ? window.setTimeout(() => controller.abort(new DOMException("timeout", "TimeoutError")), timeout)
    : 0;

  try {
    const response = await fetch(path, {
      method,
      headers: {
        Accept: "audio/*",
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
        ...headers,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
    if (!response.ok) {
      throw ApiError.fromResponse(response, await readJson(response));
    }
    if (!response.headers.get("content-type")?.includes("audio/")) {
      throw new ApiError("Phản hồi không phải audio", {
        status: response.status,
        code: "bad-content-type",
      });
    }
    return {
      blob: await response.blob(),
      seconds: Number(response.headers.get("X-Audio-Seconds")) || null,
    };
  } catch (error) {
    throw ApiError.fromNetwork(error);
  } finally {
    window.clearTimeout(timer);
    unlink();
  }
}

export { DEFAULT_TIMEOUT };
