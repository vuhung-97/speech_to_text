import { describe, expect, it } from "vitest";

import { levelRatio } from "./level";

describe("levelRatio", () => {
  it("treats silence and invalid input as zero", () => {
    expect(levelRatio(0)).toBe(0);
    expect(levelRatio(-1)).toBe(0);
    expect(levelRatio(undefined)).toBe(0);
  });

  it("clamps loud input to a full bar", () => {
    expect(levelRatio(1)).toBe(1);
  });

  it("is monotonic", () => {
    expect(levelRatio(0.05)).toBeGreaterThan(levelRatio(0.01));
    expect(levelRatio(0.02)).toBeLessThan(levelRatio(0.05));
  });
});
