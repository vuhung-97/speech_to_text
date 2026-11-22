import { afterEach, describe, expect, it } from "vitest";

import { closeReason, missingDeviceMessage, startErrorMessage } from "./errors";

afterEach(() => {
  delete window.isSecureContext;
});

describe("microphone error messages", () => {
  it("maps the close codes the server sends to user messages", () => {
    expect(closeReason(1012)).toContain("cài đặt");
    expect(closeReason(1013)).toContain("bận");
    expect(closeReason(9999)).toBe("mất kết nối tới máy chủ nhận dạng");
  });

  it("explains a denied permission", () => {
    expect(startErrorMessage({ name: "NotAllowedError" })).toBe(
      "bạn chưa cho phép dùng micro",
    );
  });

  it("falls back to the browser message, then a generic one", () => {
    expect(startErrorMessage(new Error("NotFoundError"))).toBe("NotFoundError");
    expect(startErrorMessage({})).toBe("không mở được micro");
  });

  it("distinguishes an insecure page from an unsupported browser", () => {
    window.isSecureContext = true;
    expect(missingDeviceMessage()).toContain("không hỗ trợ micro");

    window.isSecureContext = false;
    expect(missingDeviceMessage()).toContain("HTTPS");
    delete window.isSecureContext;
  });
});
