// User-facing microphone failures in one place: close codes from the server and
// the two messages the browser itself can produce.

export const CLOSE_REASONS = {
  1003: "định dạng audio không được hỗ trợ",
  1008: "origin của trang bị máy chủ từ chối",
  1012: "cài đặt vừa thay đổi — bấm Nghe lại",
  1013: "máy chủ đang bận (đủ phiên) — thử lại sau",
};

export function closeReason(code) {
  return CLOSE_REASONS[code] || "mất kết nối tới máy chủ nhận dạng";
}

export function missingDeviceMessage() {
  return window.isSecureContext
    ? "trình duyệt không hỗ trợ micro"
    : "trang chưa chạy HTTPS — micro bị chặn (xem docs/TRIEN_KHAI_LAN.md)";
}

export function startErrorMessage(error) {
  if (error?.name === "NotAllowedError") return "bạn chưa cho phép dùng micro";
  return error?.message || "không mở được micro";
}
