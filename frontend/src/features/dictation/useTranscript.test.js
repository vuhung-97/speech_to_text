import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useTranscript } from "./useTranscript";

const final = (seq, text) => ({ seq, text });

describe("useTranscript", () => {
  it("appends each finalized sentence exactly once", () => {
    const { result, rerender } = renderHook(
      ({ lastFinal }) => useTranscript(lastFinal),
      { initialProps: { lastFinal: final(0, "") } },
    );

    act(() => rerender({ lastFinal: final(1, "câu một") }));
    act(() => rerender({ lastFinal: final(2, "câu hai") }));
    act(() => rerender({ lastFinal: final(2, "câu hai") })); // same event, re-render

    expect(result.current.transcript.paragraphs.map((item) => item.text)).toEqual([
      "câu một",
      "câu hai",
    ]);
    expect(result.current.words).toBe(4);
  });

  it("ignores an empty final and clears on demand", () => {
    const { result, rerender } = renderHook(
      ({ lastFinal }) => useTranscript(lastFinal),
      { initialProps: { lastFinal: final(0, "") } },
    );

    act(() => rerender({ lastFinal: final(1, "   ") }));
    expect(result.current.transcript.paragraphs).toHaveLength(0);

    act(() => rerender({ lastFinal: final(2, "xin chào") }));
    expect(result.current.fullText).toBe("xin chào");

    act(() => result.current.clear());
    expect(result.current.fullText).toBe("");
    expect(result.current.words).toBe(0);
  });
});
