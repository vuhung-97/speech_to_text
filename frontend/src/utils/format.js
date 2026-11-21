export const STATUS_LABELS = {
  connecting: "Đang kết nối…",
  starting: "Đang khởi động…",
  listening: "Đang nghe",
  reloading: "Đang nạp model…",
  paused: "Sẵn sàng",
  error: "Lỗi micro",
  disconnected: "Mất kết nối — đang thử lại…",
};

export function formatValue(field, value) {
  const unit = field.unit ? ` ${field.unit}` : "";
  if (field.kind === "float" && (field.step ?? 1) < 0.01) {
    return `${Number(value).toFixed(3)}${unit}`;
  }
  return `${value}${unit}`;
}

// One definition of "number of words" for every screen (dictation counter,
// TTS limits, mic panel). Vietnamese text is whitespace separated.
export function countWords(text) {
  const value = (text || "").trim();
  return value ? value.split(/\s+/).length : 0;
}
