// One answer: curated text, match evidence, reading controls.

import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";

const STATUS = {
  matched: { tone: "ok", label: "Khớp kho" },
  near_miss: { tone: "accent", label: "Khớp gần đúng" },
  unanswered: { tone: "err", label: "Chưa có đáp án" },
};

export default function AnswerCard({
  answer,
  playing = false,
  progress = 0,
  seconds = 0,
  estimated = 0,
  downloadUrl = "",
  onRead,
  onStop,
  onPick,
}) {
  const status = STATUS[answer.status] || STATUS.unanswered;
  const matched = answer.matched;
  const ring = Math.min(1, Math.max(0, progress || 0));
  const elapsed = Math.max(0, Math.round(seconds || 0));
  const total = Math.max(0, Math.round(estimated || 0));
  const timing = total > 0 ? `${elapsed}s/${total}s` : `${elapsed}s`;

  return (
    <div className="rounded-card border border-line bg-surface-2/70 p-4">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <Badge tone={status.tone}>{status.label}</Badge>
        {matched && (
          <Badge tone="dim" className="max-w-full">
            <span className="min-w-0 truncate">
              {matched.percent}% · {matched.question}
            </span>
          </Badge>
        )}
        {answer.score != null && !matched && (
          <Badge tone="dim">điểm {Math.round(answer.score * 100)}%</Badge>
        )}
      </div>

      <p className="m-0 whitespace-pre-wrap text-[15px] leading-relaxed text-white">
        {answer.text}
      </p>

      {answer.candidates?.length > 0 && (
        <div className="mt-3 rounded-xl border border-line bg-white/[0.02] p-2.5">
          <p className="m-0 mb-1.5 text-[12px] uppercase tracking-[0.08em] text-faint">
            Có phải bạn hỏi
          </p>
          <div className="flex flex-wrap gap-1.5">
            {answer.candidates.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => onPick?.(item.question)}
                className="min-h-11 rounded-lg border border-line bg-white/[0.04] px-2.5 py-1 text-[12px] text-dim transition hover:bg-white/[0.08] hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:min-h-0"
              >
                {item.question}
                <span className="ml-1.5 font-mono text-[12px] text-faint">
                  {item.percent}%
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {playing ? (
          <button
            type="button"
            onClick={onStop}
            aria-pressed="true"
            aria-label="Đang đọc — bấm để dừng"
            title="Bấm để dừng"
            className="inline-flex min-h-11 max-w-full items-center gap-2 rounded-control border border-accent/40 bg-accent/10 px-2.5 py-1.5 text-[12px] font-medium text-accent transition hover:bg-accent/15 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:min-h-0"
          >
            <span
              className="h-2 w-2 shrink-0 animate-pulse rounded-full bg-current motion-reduce:animate-none"
              aria-hidden="true"
            />
            <span className="shrink-0">Đang đọc</span>
            <span
              className="h-1.5 w-16 shrink-0 overflow-hidden rounded-full bg-white/10 sm:w-24"
              aria-hidden="true"
            >
              {total > 0 ? (
                <span
                  className="block h-full rounded-full bg-gradient-to-r from-accent to-accent-2"
                  style={{ width: `${Math.round(ring * 100)}%` }}
                />
              ) : (
                <span className="block h-full w-1/3 animate-pulse rounded-full bg-accent/60 motion-reduce:animate-none" />
              )}
            </span>
            <span className="shrink-0 font-mono text-[11px] tabular-nums">
              {timing}
            </span>
          </button>
        ) : (
          <Button variant="secondary" size="sm" onClick={onRead} disabled={!answer.text}>
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
              <path d="M11 5 6 9H3v6h3l5 4V5zM15.5 8.5a5 5 0 0 1 0 7" />
            </svg>
            Đọc
          </Button>
        )}

        {downloadUrl && (
          <a
            href={downloadUrl}
            download
            className="ml-auto inline-flex min-h-11 items-center rounded-md px-2 py-1 text-[12px] text-accent transition hover:bg-accent/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:min-h-0"
          >
            Tải WAV
          </a>
        )}
      </div>
    </div>
  );
}
