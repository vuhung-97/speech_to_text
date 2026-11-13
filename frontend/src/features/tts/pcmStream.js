// Stream long-form speech as raw PCM16 over fetch.
//
// The server pushes 48 kHz mono little-endian PCM16 blocks as the model makes
// them. This module re-frames the byte stream (a chunk can split a sample in
// half), converts to float32 and hands blocks to the player. No Blob is ever
// created: a two-hour answer would be ~700 MB in the browser.

import { ApiError } from "../../services/errors";

const FALLBACK_SAMPLE_RATE = 48_000;

function int16ToFloat32(bytes) {
  const count = bytes.byteLength >> 1;
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const out = new Float32Array(count);
  for (let index = 0; index < count; index += 1) {
    out[index] = view.getInt16(index * 2, true) / 32768;
  }
  return out;
}

function merge(left, right) {
  if (!left.length) return right;
  const merged = new Uint8Array(left.length + right.length);
  merged.set(left, 0);
  merged.set(right, left.length);
  return merged;
}

async function readError(response) {
  try {
    const data = await response.json();
    return data?.error || `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
}

export async function streamSpeech(text, voice, handlers = {}) {
  const { onStart, onBlock, onProgress, onDone, signal } = handlers;

  let response;
  try {
    response = await fetch("/api/v1/tts/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "audio/L16" },
      body: JSON.stringify({ text, voice: voice || null }),
      signal,
    });
  } catch (error) {
    throw ApiError.fromNetwork(error);
  }

  if (!response.ok) {
    throw new ApiError(await readError(response), {
      status: response.status,
      code: "tts-stream",
    });
  }

  const sampleRate =
    Number(response.headers.get("X-Sample-Rate")) || FALLBACK_SAMPLE_RATE;
  const sessionId = response.headers.get("X-Tts-Session") || "";
  const estimated = Number(response.headers.get("X-Estimated-Seconds")) || 0;
  onStart?.({ sessionId, sampleRate, estimated });

  if (!response.body) {
    throw new ApiError("Trình duyệt không hỗ trợ đọc luồng audio.", {
      status: 0,
      code: "no-stream",
    });
  }

  const reader = response.body.getReader();
  let leftover = new Uint8Array(0);
  let receivedBytes = 0;

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      if (!value?.length) continue;

      let bytes = merge(leftover, value);
      const even = bytes.length & ~1;
      if (even === 0) {
        leftover = bytes;
        continue;
      }
      const block = int16ToFloat32(bytes.subarray(0, even));
      leftover = bytes.slice(even);

      receivedBytes += even;
      onBlock?.(block, sampleRate);
      onProgress?.({
        seconds: receivedBytes / 2 / sampleRate,
        estimated,
      });
    }
  } finally {
    reader.releaseLock?.();
  }

  onDone?.({ sessionId, seconds: receivedBytes / 2 / sampleRate });
  return { sessionId, sampleRate, seconds: receivedBytes / 2 / sampleRate };
}

export const ttsWavUrl = (sessionId) =>
  `/api/v1/tts/sessions/${encodeURIComponent(sessionId)}.wav`;
