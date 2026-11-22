// Right tools panel: source, reading settings and microphone. The pieces are
// separated into compact cards so the panel never reads as one long form.

import Alert from "../../components/ui/Alert";
import { ModeControl } from "../settings";
import { VoiceSettings } from "../tts";
import DocumentPicker from "./DocumentPicker";
import MicControls from "./MicControls";

function ToolCard({ title, meta, children }) {
  return (
    <section className="rounded-2xl border border-line bg-wash p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h2 className="m-0 text-[11px] font-semibold tracking-[0.04em] text-dim">
          {title}
        </h2>
        {meta && <span className="text-[10px] text-faint">{meta}</span>}
      </div>
      {children}
    </section>
  );
}

export default function QaSidebar({
  documents,
  documentId,
  onSelectDocument,
  busy,
  mic,
  listen,
  devices,
  device,
  onChooseMic,
}) {
  const total = (documents || []).reduce(
    (sum, document) => sum + (document.entry_count || 0),
    0,
  );
  const warning =
    listen.error ||
    (mic.silentMic
      ? "Có gửi audio nhưng mức âm thanh gần 0: chọn micro khác."
      : "") ||
    (mic.insecure ? "Trang chưa chạy HTTPS nên trình duyệt chặn micro." : "") ||
    listen.notice;

  return (
    <div className="space-y-3">
      <ToolCard title="Bộ đề" meta={`${total} câu`}>
        <DocumentPicker
          documents={documents}
          value={documentId}
          onChange={onSelectDocument}
          disabled={busy}
          label="Nguồn trả lời"
        />
        <p className="mt-1.5 mb-0 text-[10px] leading-relaxed text-faint">
          Chỉ tìm trong bộ đề đang chọn.
        </p>
      </ToolCard>

      <ToolCard title="Đọc đáp án">
        <ModeControl bare />
        <VoiceSettings embedded />
      </ToolCard>

      <ToolCard title="Mic">
        <MicControls
          label={mic.micLabel}
          listen={listen}
          levelPercent={mic.levelPercent}
          devices={devices}
          device={device}
          onChooseMic={onChooseMic}
        />
        {warning && (
          <Alert
            size="sm"
            className="mt-2"
            tone={listen.error || mic.insecure ? "err" : "note"}
          >
            {warning}
          </Alert>
        )}
      </ToolCard>

      <p className="m-0 px-1 text-center text-[10px] leading-relaxed text-faint">
        Mọi xử lý diễn ra trên máy này. Không gửi dữ liệu ra ngoài.
      </p>
    </div>
  );
}
