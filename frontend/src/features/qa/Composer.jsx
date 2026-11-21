// Composer: typing is the default. The mic opens only for a deliberate
// "Nghe" press, and Enter sends while Shift+Enter adds a line.
//
// While listening, the input shows the committed text plus the live partial
// being recognised and is read-only, so server updates never fight the caret.
// Enter still submits: the screen stops the mic and appends the spoken tail.

import Alert from "../../components/ui/Alert";
import Button from "../../components/ui/Button";
import { GRACE_MS } from "../mic/constants";

function MicIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-3.5 w-3.5"
      aria-hidden="true"
    >
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10v1a7 7 0 0 0 14 0v-1M12 18v4" />
    </svg>
  );
}

function displayValue(value, live, listening) {
  if (!listening || !live) return value;
  return [value.trimEnd(), live.trim()].filter(Boolean).join(" ");
}

export default function Composer({
  value,
  live = "",
  onChange,
  onSubmit,
  busy,
  listening,
  onToggleListen,
  error,
}) {
  const shown = displayValue(value, live, listening);
  const canSubmit = Boolean(shown.trim()) && !busy;
  const graceLabel = (GRACE_MS / 1000).toLocaleString("vi-VN");

  const submit = () => {
    if (!canSubmit) return;
    onSubmit(value.trim());
  };

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
      className="shrink-0 border-t border-line bg-surface/70 px-5 py-3"
    >
      {error && (
        <Alert size="compact" className="mx-auto mb-2 max-w-[720px]">
          {error}
        </Alert>
      )}

      <div className="mx-auto flex max-w-[720px] items-end gap-2">
        <Button
          variant={listening ? "danger" : "secondary"}
          size="md"
          aria-pressed={listening}
          onClick={onToggleListen}
          title={listening ? "Dừng nghe" : "Nghe câu hỏi"}
        >
          <MicIcon />
          {listening ? "Dừng" : "Nghe"}
        </Button>

        <label className="min-w-0 flex-1">
          <span className="sr-only">Câu hỏi</span>
          <textarea
            value={shown}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key !== "Enter" || event.shiftKey) return;
              if (event.nativeEvent?.isComposing) return;
              event.preventDefault();
              submit();
            }}
            readOnly={listening}
            autoFocus
            rows={1}
            placeholder={
              listening
                ? "Đang nghe… nói câu hỏi của bạn"
                : "Nhập câu hỏi, hoặc bấm Nghe để nói…"
            }
            className="max-h-[140px] min-h-[42px] w-full resize-y rounded-control border border-line bg-white/[0.03] px-3 py-2.5 text-[13.5px] leading-relaxed text-white outline-none placeholder:text-faint focus:border-accent/60"
          />
        </label>

        <Button type="submit" variant="primary" size="md" disabled={!canSubmit}>
          {busy ? "Đang tìm…" : "Hỏi"}
        </Button>
      </div>

      <p
        aria-live="polite"
        className="mx-auto mt-2 mb-0 max-w-[720px] text-[10.5px] text-faint"
      >
        {listening
          ? `Mic đang mở · tự dừng sau ${graceLabel} giây im lặng · bấm Dừng để cắt ngay.`
          : "Mic tắt mặc định · Enter để hỏi · Shift+Enter để xuống dòng."}
      </p>
    </form>
  );
}
