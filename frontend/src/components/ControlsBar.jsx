import { useApp } from "../context/AppContext";

function Button({ active = false, ghost = false, ...props }) {
  const base =
    "rounded-xl px-4 py-2 text-[13.5px] font-medium transition hover:-translate-y-px active:translate-y-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent";
  const tone = ghost
    ? "bg-transparent text-dim hover:bg-white/5 hover:text-white"
    : active
      ? "border border-accent/45 bg-accent/15 text-accent"
      : "border border-line bg-white/[0.045] text-white hover:border-white/20 hover:bg-white/[0.085]";
  return <button type="button" {...props} className={`${base} ${tone}`} />;
}

export default function ControlsBar({ onOpenTts }) {
  const {
    status,
    engine,
    pending,
    words,
    togglePause,
    clearAll,
    fullText,
    notify,
  } = useApp();

  const copy = async () => {
    if (!fullText) {
      notify("Chưa có nội dung để sao chép");
      return;
    }
    try {
      await navigator.clipboard.writeText(fullText);
      notify("Đã sao chép");
    } catch {
      notify("Trình duyệt không cho phép sao chép");
    }
  };

  const meta = [
    `${engine.model || "?"}·${engine.cpu_threads ?? "?"}t`,
    status.mode === "realtime" ? "realtime" : "accurate",
    pending ? `chờ ${pending}` : null,
    `${words} từ`,
    status.rtf != null ? `RTF ${status.rtf.toFixed(2)}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="flex flex-wrap items-center gap-2.5 border-t border-line bg-white/[0.018] px-4 py-3">
      <Button active={status.paused} onClick={togglePause}>
        {status.paused ? "Tiếp tục" : "Tạm dừng"}
      </Button>
      <Button onClick={copy}>Sao chép</Button>
      <Button onClick={onOpenTts} title="Chuyển văn bản thành giọng nói">
        Đọc
      </Button>
      <Button ghost onClick={clearAll}>
        Xoá
      </Button>
      <span className="flex-1" />
      <span className="font-mono text-[11.5px] tabular-nums text-faint max-sm:hidden">
        {meta}
      </span>
    </div>
  );
}
