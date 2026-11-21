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
          <span className={`font-mono text-[11px] ${counterTone}`}>{counter}</span>
        </span>
        <textarea
          value={text}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Nhập hoặc dán văn bản cần đọc…"
          className="min-h-[150px] flex-1 resize-none rounded-xl border border-line bg-white/[0.03] px-3 py-2.5 text-[14px] leading-relaxed text-white outline-none placeholder:text-faint focus:border-accent/60"
        />
      </label>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onUseTranscript}
          className="rounded-lg border border-line bg-white/[0.04] px-3 py-1.5 text-[12.5px] text-dim transition hover:bg-white/[0.08] hover:text-white"
        >
          Dùng transcript
        </button>
        <button
          type="button"
          onClick={onClear}
          className="rounded-lg px-3 py-1.5 text-[12.5px] text-faint transition hover:bg-white/5 hover:text-white"
        >
          Xoá
        </button>
        {firstLoad && available && (
          <span className="text-[11px] text-faint">
            Lần đầu nạp model ~10–20 giây.
          </span>
        )}
      </div>
    </>
  );
}
