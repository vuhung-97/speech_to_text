// Right sidebar: question set and microphone in separate cards.
// The cards and the vertical gap are what keep the two controls from looking
// attached to each other.

import Alert from "../../components/ui/Alert";
import { ModeControl } from "../settings";
import { VoiceSettings } from "../tts";
import DocumentPicker from "./DocumentPicker";
import MicControls from "./MicControls";

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
  const warning =
    listen.error ||
    (mic.silentMic
      ? "Có gửi audio nhưng mức âm thanh gần 0: chọn micro khác."
      : "") ||
    (mic.insecure ? "Trang chưa chạy HTTPS nên trình duyệt chặn micro." : "") ||
    listen.notice;

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-line bg-white/[0.02] p-3">
        <DocumentPicker
          documents={documents}
          value={documentId}
          onChange={onSelectDocument}
          disabled={busy}
        />
      </section>

      <ModeControl />
      <VoiceSettings />

      <section className="rounded-xl border border-line bg-white/[0.02] p-3">
        <h2 className="m-0 mb-2 text-[12px] font-semibold tracking-[0.08em] text-faint uppercase">
          Mic
        </h2>
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
      </section>
    </div>
  );
}
