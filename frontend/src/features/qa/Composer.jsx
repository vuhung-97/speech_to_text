// Composer: type a question, or promote the live transcript into one.
// Never hijacks Space — the textarea needs it; Ctrl+Enter submits.

import { useState } from "react";

import Button from "../../components/ui/Button";
import { useApp } from "../../context/AppContext";

export default function Composer({ onAsk, busy, suggestion, onDismissSuggestion }) {
  const { fullText, live, status } = useApp();
  const [text, setText] = useState("");

  const spoken = `${live.stable || ""} ${live.tentative || ""}`.trim();
  const canSubmit = Boolean(text.trim() || fullText.trim()) && !busy;

  const submit = (value, source) => {
    const question = (value || "").trim();
    if (!question || busy) return;
    setText("");
    onDismissSuggestion();
    onAsk(question, source);
  };

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        submit(text || fullText, text.trim() ? "typed" : "voice");
      }}
      className="shrink-0 border-t border-line bg-surface/70 px-5 py-3"
    >
      {suggestion && (
        <div className="mb-2 flex flex-wrap items-center gap-2 rounded-xl border border-accent/30 bg-accent/10 px-3 py-2 text-[12px] text-accent">
          <span className="font-semibold">Nghe được câu hỏi:</span>
          <span className="min-w-0 flex-1 truncate text-white">{suggestion}</span>
          <Button
            size="sm"
            variant="primary"
            onClick={() => submit(suggestion, "voice")}
            disabled={busy}
          >
            Hỏi
          </Button>
          <button
            type="button"
            onClick={onDismissSuggestion}
            className="rounded-md px-1.5 py-0.5 text-dim transition hover:text-white"
          >
            Bỏ qua
          </button>
        </div>
      )}

      <div className="mx-auto flex max-w-[720px] items-end gap-2">
        <label className="min-w-0 flex-1">
          <span className="sr-only">Câu hỏi</span>
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={(event) => {
              if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                event.preventDefault();
                submit(text || fullText, text.trim() ? "typed" : "voice");
              }
            }}
            rows={1}
            placeholder={
              spoken
                ? `Đang nghe: ${spoken.slice(-90)}`
                : "Nhập câu hỏi, hoặc nói và bấm Hỏi…"
            }
            className="max-h-[120px] min-h-[42px] w-full resize-y rounded-control border border-line bg-white/[0.03] px-3 py-2.5 text-[13.5px] leading-relaxed text-white outline-none placeholder:text-faint focus:border-accent/60"
          />
        </label>

        {fullText && (
          <Button
            variant="ghost"
            size="md"
            onClick={() => setText(fullText)}
            title="Đưa toàn bộ transcript vào ô câu hỏi"
          >
            Lấy transcript
          </Button>
        )}

        <Button type="submit" variant="primary" size="md" disabled={!canSubmit}>
          {busy ? "Đang tìm…" : "Hỏi"}
        </Button>
      </div>

      <p className="mx-auto mt-2 mb-0 max-w-[720px] text-[10.5px] text-faint">
        {status.paused
          ? "Mic đang tạm dừng — bấm Esc ở trang Đọc chính tả để tiếp tục."
          : "Mic luôn nghe · câu hỏi được nhận diện khi bạn nói xong · Ctrl+Enter để gửi."}
      </p>
    </form>
  );
}
