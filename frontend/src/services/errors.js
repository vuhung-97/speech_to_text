// Normalised error surface for the whole client.
//
// Every failure that can reach a component is an ApiError with a Vietnamese
// message, so screens never have to inspect HTTP details or `TypeError`.

export const ERROR_MESSAGES = {
  0: "Không kết nối được tới máy chủ.",
  400: "Yêu cầu chưa hợp lệ.",
  401: "Bạn cần đăng nhập lại.",
  403: "Bạn không có quyền thực hiện thao tác này.",
  404: "Không tìm thấy dữ liệu.",
  409: "Máy chủ đang bận, thử lại sau ít giây.",
  413: "Dữ liệu vượt quá giới hạn cho phép.",
  425: "Dữ liệu chưa sẵn sàng.",
  429: "Quá nhiều yêu cầu, vui lòng chờ.",
  500: "Máy chủ gặp lỗi.",
  503: "Dịch vụ chưa sẵn sàng.",
  507: "Không đủ dung lượng đĩa.",
};

export class ApiError extends Error {
  constructor(message, { status = 0, code = "", details = null, cause = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.cause = cause;
  }

  get offline() {
    return this.status === 0;
  }

  static fromResponse(response, data) {
    const fallback = ERROR_MESSAGES[response.status] || `HTTP ${response.status}`;
    const message = data?.error || data?.message || fallback;
    return new ApiError(message, {
      status: response.status,
      code: data?.code || "",
      details: data?.details ?? null,
    });
  }

  static fromNetwork(error) {
    if (error instanceof ApiError) return error;
    const aborted =
      error?.name === "AbortError" || error?.name === "TimeoutError";
    return new ApiError(
      aborted ? "Yêu cầu đã bị huỷ." : ERROR_MESSAGES[0],
      { status: 0, code: aborted ? "aborted" : "network", cause: error },
    );
  }
}

export function messageFor(error) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error && error.message) return error.message;
  return "Đã có lỗi không xác định.";
}
