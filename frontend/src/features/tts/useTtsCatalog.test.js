import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../../services/api";
import { useTtsCatalog } from "./useTtsCatalog";

vi.mock("../../services/api", () => ({
  getTtsVoices: vi.fn(),
}));

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("useTtsCatalog", () => {
  it("keeps the stored voice when the server still offers it", async () => {
    window.localStorage.setItem("tts.voice", "giọng-b");
    api.getTtsVoices.mockResolvedValue({
      voices: [
        { id: "giọng-a", label: "A" },
        { id: "giọng-b", label: "B" },
      ],
      default: "giọng-a",
      available: true,
      max_chars: 900,
      max_words: 1500,
    });

    const { result, rerender } = renderHook(({ open }) => useTtsCatalog(open), {
      initialProps: { open: false },
    });
    rerender({ open: true });

    await waitFor(() => expect(result.current.voices).toHaveLength(2));
    expect(result.current.voice).toBe("giọng-b");
    expect(result.current.maxChars).toBe(900);
    expect(result.current.maxWords).toBe(1500);
  });

  it("falls back to the server default when the stored voice is gone", async () => {
    window.localStorage.setItem("tts.voice", "đã-xoá");
    api.getTtsVoices.mockResolvedValue({
      voices: [{ id: "giọng-a", label: "A" }],
      default: "giọng-a",
    });

    const { result, rerender } = renderHook(({ open }) => useTtsCatalog(open), {
      initialProps: { open: false },
    });
    rerender({ open: true });

    await waitFor(() => expect(result.current.voices).toHaveLength(1));
    expect(result.current.voice).toBe("giọng-a");
  });

  it("marks TTS unavailable when the catalog request fails", async () => {
    api.getTtsVoices.mockRejectedValue(new Error("offline"));

    const { result, rerender } = renderHook(({ open }) => useTtsCatalog(open), {
      initialProps: { open: false },
    });
    rerender({ open: true });

    await waitFor(() => expect(result.current.available).toBe(false));
    expect(result.current.reason).toContain("offline");
  });

  it("persists a newly chosen voice", async () => {
    api.getTtsVoices.mockResolvedValue({
      voices: [{ id: "giọng-a", label: "A" }],
      default: "giọng-a",
    });
    const { result, rerender } = renderHook(({ open }) => useTtsCatalog(open), {
      initialProps: { open: false },
    });
    rerender({ open: true });
    await waitFor(() => expect(result.current.voices).toHaveLength(1));

    act(() => result.current.chooseVoice("giọng-a"));

    expect(window.localStorage.getItem("tts.voice")).toBe("giọng-a");
  });
});
