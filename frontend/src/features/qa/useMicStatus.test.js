import { describe, expect, it } from "vitest";

import { micLabel } from "./useMicStatus";

const base = {
  active: false,
  packets: 0,
  micState: "idle",
  speechBusy: false,
  audioPlaying: false,
};

describe("micLabel", () => {
  it("prioritises the live connection state", () => {
    expect(micLabel({ ...base, active: true, packets: 3 })).toBe("Đang nghe");
    expect(micLabel({ ...base, active: true, packets: 0 })).toBe(
      "Đang kết nối audio…",
    );
  });

  it("shows connecting and error states when the mic is off", () => {
    expect(micLabel({ ...base, micState: "connecting" })).toBe("Đang kết nối mic…");
    expect(micLabel({ ...base, micState: "error" })).toBe("Lỗi mic");
  });

  it("reports reading before the idle label", () => {
    expect(micLabel({ ...base, speechBusy: true })).toBe("Đang đọc");
    expect(micLabel({ ...base, audioPlaying: true })).toBe("Đang đọc");
    expect(micLabel(base)).toBe("Mic tắt");
  });
});
