import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import { FIELD_CLASS, FIELD_TEXT } from "../../components/ui/fieldStyles";
import { countWords } from "../../utils/format";
import PanelSection from "./PanelSection";

export default function MicPanel({
  micLabel,
  listen,
  liveText,
  levelPercent,
  silentMic,
  insecure,
  devices = [],
  device = "",
  onChooseMic,
}) {
  return (
    <PanelSection title="Mic">
      <div className="flex items-center justify-between text-[12px]">
        <span className={listen.active ? "text-accent" : "text-dim"}>{micLabel}</span>
        <Badge tone={listen.active ? "accent" : "neutral"}>
          {countWords(liveText)} từ
        </Badge>
      </div>

      <p className="mt-2 mb-0 line-clamp-4 text-[12px] leading-relaxed text-faint">
        {listen.error
          ? listen.error
          : liveText ||
            (listen.active
              ? listen.packets
                ? `Đang nghe… (đã gửi ${listen.packets} gói audio)`
                : "Đang chờ audio từ micro… nếu mãi không đổi, kiểm tra quyền mic."
              : "Mic tắt — bấm Nghe khi muốn nói câu hỏi.")}
      </p>

      {listen.active && (
        <div className="mt-2">
          <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-gradient-to-r from-accent-2 to-accent transition-[width] duration-100"
              style={{ width: `${levelPercent}%` }}
            />
          </div>
          <p className="m-0 mt-1 truncate font-mono text-[12px] text-faint">
            {listen.deviceLabel || "micro mặc định"} · {listen.sampleRate || "?"} Hz
          </p>
        </div>
      )}

      {silentMic && (
        <Alert tone="note" size="sm" className="mt-2">
          Có gửi audio nhưng mức âm thanh gần 0: chọn micro khác trong danh sách,
          hoặc kiểm tra Windows → Sound → Input.
        </Alert>
      )}
      {insecure && (
        <Alert size="sm" className="mt-2">
          Trang không chạy HTTPS nên trình duyệt chặn micro. Dùng localhost hoặc
          cấu hình HTTPS cho LAN (xem docs/TRIEN_KHAI_LAN.md).
        </Alert>
      )}
      {listen.notice && (
        <Alert tone="note" size="sm" className="mt-2">
          {listen.notice}
        </Alert>
      )}

      {listen.micState !== "live" && (
        <label className="mt-2 block">
          <span className="sr-only">Thiết bị mic</span>
          <select
            value={device}
            onChange={(event) => onChooseMic?.(event.target.value)}
            disabled={listen.active}
            className={`${FIELD_CLASS} min-h-11 w-full rounded-lg px-2 py-2 text-dim sm:min-h-0 ${FIELD_TEXT}`}
          >
            <option value="">Mic mặc định</option>
            {devices.map((item, index) => (
              <option key={item.deviceId || index} value={item.deviceId}>
                {item.label || `Micro ${index + 1}`}
              </option>
            ))}
          </select>
        </label>
      )}
    </PanelSection>
  );
}
