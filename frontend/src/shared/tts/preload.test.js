import { describe, expect, it } from "vitest";

import { isPreloadUnsupported } from "./preload";

describe("isPreloadUnsupported", () => {
  it("treats a missing endpoint as unsupported, not as a failure", () => {
    expect(isPreloadUnsupported({ status: 404 })).toBe(true);
    expect(isPreloadUnsupported({ status: 405 })).toBe(true);
  });

  it("keeps real failures visible", () => {
    expect(isPreloadUnsupported({ status: 500 })).toBe(false);
    expect(isPreloadUnsupported(new Error("mạng"))).toBe(false);
    expect(isPreloadUnsupported(undefined)).toBe(false);
  });
});
