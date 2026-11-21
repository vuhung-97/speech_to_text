export default function StreamProgress({ speech, label }) {
  if (speech.status === "idle") return null;

  return (
    <div className="rounded-xl border border-line bg-white/[0.03] p-3">
      <div className="flex items-center justify-between gap-3 text-[12px]">
        <span className={speech.status === "error" ? "text-err" : "text-white"}>
          {label}
        </span>
        <span className="font-mono text-[11px] text-faint">
          {speech.seconds.toFixed(1)} s
          {speech.estimated ? ` / ~${Math.round(speech.estimated)} s` : ""}
        </span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-gradient-to-r from-accent to-accent-2 transition-[width] duration-200"
          style={{ width: `${Math.round(speech.progress * 100)}%` }}
        />
      </div>
      <div className="mt-2 flex items-center justify-between text-[11.5px]">
        <button
          type="button"
          onClick={speech.stop}
          className="rounded-md px-2 py-1 text-dim transition hover:bg-white/[0.06] hover:text-white"
        >
          Dừng
        </button>
        {speech.downloadUrl && (
          <a
            href={speech.downloadUrl}
            download
            className="rounded-md px-2 py-1 text-accent transition hover:bg-accent/10"
          >
            Tải WAV
          </a>
        )}
      </div>
    </div>
  );
}
