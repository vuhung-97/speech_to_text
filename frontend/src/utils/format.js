export const STATUS_LABELS = {
  connecting: "Đang kết nối…",
  starting: "Đang khởi động…",
  listening: "Đang nghe",
  reloading: "Đang nạp model…",
  paused: "Mic tắt",
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

export function joinTranscript(paragraphs, live) {
  const parts = paragraphs.map((paragraph) => paragraph.text);
  if (live.stable) parts.push(live.stable);
  if (live.tentative) parts.push(live.tentative);
  return parts.join(" ").replace(/\s+/g, " ").trim();
}

export function countWords(paragraphs, live) {
  const text = joinTranscript(paragraphs, live);
  return text ? text.split(/\s+/).length : 0;
}
