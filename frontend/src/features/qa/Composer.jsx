// Composer: typing is the default. The mic opens only for a deliberate
// "Nghe" press, and Enter sends while Shift+Enter adds a line.
//
// While listening, the input shows the committed text plus the live partial
// being recognised and is read-only, so server updates never fight the caret.
// Enter still submits: the screen stops the mic and appends the spoken tail.

import Button from "../../components/ui/Button";
import { FIELD_CLASS, FIELD_TEXT } from "../../components/ui/fieldStyles";

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
}) {
  const shown = displayValue(value, live, listening);
  const canSubmit = Boolean(shown.trim()) && !busy;

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
      className="shrink-0 border-t border-line bg-surface/70 px-4 py-3 sm:px-6 lg:px-8"
    >
      <div className="mx-auto flex w-full max-w-[780px] items-center gap-2">
        <Button
          variant={listening ? "danger" : "secondary"}
          size="md"
          className="h-11 shrink-0 px-3.5"
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
              listening ? "Đang nghe…" : "Hỏi hoặc bấm micro…"
            }
            className={`${FIELD_CLASS} h-11 min-h-11 w-full resize-none rounded-control px-3 py-2 leading-normal ${FIELD_TEXT}`}
          />
        </label>

        <Button
          type="submit"
          variant="primary"
          size="md"
          className="h-11 shrink-0 px-4"
          disabled={!canSubmit}
        >
          {busy ? "Đang tìm…" : "Hỏi"}
        </Button>
      </div>
      <p className="mx-auto mt-1.5 hidden w-full max-w-[780px] pl-[62px] text-[10px] text-faint sm:block">
        <kbd className="rounded border border-line bg-wash-strong px-1 py-0.5 font-mono text-[9.5px]">
          Enter
        </kbd>{" "}
        để gửi ·{" "}
        <kbd className="rounded border border-line bg-wash-strong px-1 py-0.5 font-mono text-[9.5px]">
          Shift
        </kbd>{" "}
        +{" "}
        <kbd className="rounded border border-line bg-wash-strong px-1 py-0.5 font-mono text-[9.5px]">
          Enter
        </kbd>{" "}
        xuống dòng
      </p>
    </form>
  );
}
