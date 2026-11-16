import Badge from "../../components/ui/Badge";
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
          {liveText ? liveText.split(/\s+/).length : 0} từ
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
          <p className="m-0 mt-1 truncate font-mono text-[10px] text-faint">
            {listen.deviceLabel || "micro mặc định"} · {listen.sampleRate || "?"} Hz
          </p>
        </div>
      )}

      {silentMic && (
        <p className="mt-2 mb-0 rounded-lg border border-accent/30 bg-accent/[0.08] px-2 py-1.5 text-[11px] leading-relaxed text-accent">
          Có gửi audio nhưng mức âm thanh gần 0: chọn micro khác trong danh sách,
          hoặc kiểm tra Windows → Sound → Input.
        </p>
      )}
      {insecure && (
        <p className="mt-2 mb-0 rounded-lg border border-err/35 bg-err/10 px-2 py-1.5 text-[11px] leading-relaxed text-err">
          Trang không chạy HTTPS nên trình duyệt chặn micro. Dùng localhost hoặc
          cấu hình HTTPS cho LAN (xem docs/TRIEN_KHAI_LAN.md).
        </p>
      )}
      {listen.notice && (
        <p className="mt-2 mb-0 rounded-lg border border-accent/30 bg-accent/[0.08] px-2 py-1.5 text-[11px] leading-relaxed text-accent">
          {listen.notice}
        </p>
      )}

      {listen.micState !== "live" && (
        <label className="mt-2 block">
          <span className="sr-only">Thiết bị mic</span>
          <select
            value={device}
            onChange={(event) => onChooseMic?.(event.target.value)}
            disabled={listen.active}
            className="w-full rounded-lg border border-line bg-white/[0.04] px-2 py-1 text-[11.5px] text-dim outline-none focus:border-accent/60"
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
