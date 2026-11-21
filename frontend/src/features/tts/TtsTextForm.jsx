import { FIELD_CLASS, FIELD_TEXT } from "../../components/ui/fieldStyles";

export default function TtsTextForm({
  text,
  onChange,
  mode,
  words,
  charCount,
  maxWords,
  maxChars,
  overLimit,
  onUseTranscript,
  onClear,
  firstLoad,
  available,
}) {
  const counter =
    mode === "stream"
      ? `${words}/${maxWords} từ · ${charCount} ký tự`
      : `${charCount}/${maxChars} ký tự`;
  const counterTone = overLimit ? "text-err" : "text-faint";

  return (
    <>
      <label className="flex min-h-0 flex-1 flex-col">
        <span className="mb-1 flex items-center justify-between text-[13px] text-white">
          <span>Văn bản</span>
          <span className={`font-mono text-[12px] ${counterTone}`}>{counter}</span>
        </span>
        <textarea
          value={text}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Nhập hoặc dán văn bản cần đọc…"
          className={`${FIELD_CLASS} min-h-[150px] flex-1 resize-none rounded-xl px-3 py-2.5 leading-relaxed ${FIELD_TEXT}`}
        />
      </label>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onUseTranscript}
          className="inline-flex min-h-11 items-center rounded-lg border border-line bg-white/[0.04] px-3 py-1.5 text-[12.5px] text-dim transition hover:bg-white/[0.08] hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:min-h-0"
        >
          Dùng transcript
        </button>
        <button
          type="button"
          onClick={onClear}
          className="inline-flex min-h-11 items-center rounded-lg px-3 py-1.5 text-[12.5px] text-faint transition hover:bg-white/5 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:min-h-0"
        >
          Xoá
        </button>
        {firstLoad && available && (
          <span className="text-[12px] text-faint">
            Lần đầu nạp model ~10–20 giây.
          </span>
        )}
      </div>
    </>
  );
}
