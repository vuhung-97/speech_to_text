import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TTS_MODES, useTtsComposer } from "./useTtsComposer";

const catalog = { maxWords: 3, maxChars: 100, available: true };

describe("useTtsComposer", () => {
  it("counts words in stream mode and characters in quick mode", () => {
    const { result } = renderHook(() => useTtsComposer(catalog));

    act(() => result.current.setText("một hai ba bốn"));
    expect(result.current.words).toBe(4);
    expect(result.current.overLimit).toBe(true);

    act(() => result.current.setMode(TTS_MODES.quick));
    expect(result.current.overLimit).toBe(false);
    expect(result.current.charCount).toBe(14);
    expect(result.current.limit).toBe(100);

    act(() => result.current.setText("x".repeat(101)));
    expect(result.current.overLimit).toBe(true);
  });

  it("truncates a long transcript and tells the user", () => {
    const notify = vi.fn();
    const { result } = renderHook(() => useTtsComposer(catalog));

    act(() => result.current.fillFromTranscript("một hai ba bốn năm", notify));

    expect(result.current.text).toBe("một hai ba");
    expect(notify).toHaveBeenCalledWith("Transcript dài hơn 3 từ — đã cắt bớt");
  });

  it("does nothing without a transcript", () => {
    const notify = vi.fn();
    const { result } = renderHook(() => useTtsComposer(catalog));

    act(() => result.current.fillFromTranscript("", notify));

    expect(result.current.text).toBe("");
    expect(notify).toHaveBeenCalledWith("Chưa có nội dung nhận dạng để đọc");
  });
});
