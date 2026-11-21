// Dictation controls. All state is supplied by the caller so this stays a
// presentation component (browser mic lives in useSpeechStream).

function Button({ active = false, ghost = false, ...props }) {
  const base =
    "inline-flex min-h-11 items-center rounded-xl px-4 py-2 text-[13.5px] font-medium transition hover:-translate-y-px active:translate-y-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:min-h-0";
  const tone = ghost
    ? "bg-transparent text-dim hover:bg-white/5 hover:text-white"
    : active
      ? "border border-accent/45 bg-accent/15 text-accent"
      : "border border-line bg-white/[0.045] text-white hover:border-white/20 hover:bg-white/[0.085]";
  return <button type="button" {...props} className={`${base} ${tone}`} />;
}

export default function ControlsBar({
  listening,
  onToggle,
  engine,
  pending = 0,
  words = 0,
  fullText = "",
  onOpenTts,
  onClear,
  onCopy,
  mode = "accurate",
  rtf = null,
}) {
  const meta = [
    `${engine?.model || "?"}·${engine?.cpu_threads ?? "?"}t`,
    mode,
    pending ? `chờ ${pending}` : null,
    `${words} từ`,
    rtf != null ? `RTF ${rtf.toFixed(2)}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="flex flex-wrap items-center gap-2.5 border-t border-line bg-white/[0.018] px-4 py-3">
      <Button active={!listening} onClick={onToggle}>
        {listening ? "Tạm dừng" : "Bắt đầu nghe"}
      </Button>
      <Button onClick={onCopy}>Sao chép</Button>
      <Button onClick={onOpenTts} title="Chuyển văn bản thành giọng nói">
        Đọc
      </Button>
      <Button ghost onClick={onClear}>
        Xoá
      </Button>
      <span className="flex-1" />
      <span className="font-mono text-[12px] tabular-nums text-faint max-sm:hidden">
        {meta}
      </span>
      {!fullText && <span className="sr-only">Chưa có nội dung</span>}
    </div>
  );
}
