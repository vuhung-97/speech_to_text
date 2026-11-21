import { describe, expect, it } from "vitest";

import { countWords, formatValue } from "./format";

describe("countWords", () => {
  it("ignores surrounding whitespace and collapses runs", () => {
    expect(countWords("  xin   chào  ")).toBe(2);
  });

  it("returns zero for empty input", () => {
    expect(countWords("")).toBe(0);
    expect(countWords(undefined)).toBe(0);
  });
});

describe("formatValue", () => {
  it("shows three decimals for fine-grained floats", () => {
    expect(formatValue({ kind: "float", step: 0.001, unit: "s" }, 0.5)).toBe("0.500 s");
  });

  it("keeps integer-like values compact", () => {
    expect(formatValue({ kind: "int", step: 1 }, 2)).toBe("2");
  });
});
