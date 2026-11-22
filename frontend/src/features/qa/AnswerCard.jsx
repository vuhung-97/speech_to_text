// One answer: curated text, match evidence, reading controls.

import { useState } from "react";

import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";

const STATUS = {
  matched: { tone: "ok", label: "Khớp kho" },
  near_miss: { tone: "accent", label: "Khớp gần đúng" },
  unanswered: { tone: "err", label: "Chưa có đáp án" },
};

function SpeakerIcon() {
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
      <path d="M11 5 6 9H3v6h3l5 4V5zM15.5 8.5a5 5 0 0 1 0 7" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-3.5 w-3.5"
      aria-hidden="true"
    >
      <rect x="9" y="9" width="11" height="11" rx="2" />
      <path d="M5 15V5a2 2 0 0 1 2-2h10" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-3.5 w-3.5"
      aria-hidden="true"
    >
      <path d="M12 3v12m0 0 4-4m-4 4-4-4M5 21h14" />
    </svg>
  );
}

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
  const [copied, setCopied] = useState(false);
  const status = STATUS[answer.status] || STATUS.unanswered;
  const matched = answer.matched;
  const ring = Math.min(1, Math.max(0, progress || 0));
  const elapsed = Math.max(0, Math.round(seconds || 0));
  const total = Math.max(0, Math.round(estimated || 0));
  const timing = total > 0 ? `${elapsed}s/${total}s` : `${elapsed}s`;

  const copy = async () => {
    if (!navigator.clipboard?.writeText) return;
    try {
      await navigator.clipboard.writeText(answer.text || "");
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard can be unavailable outside a secure context */
    }
  };

  return (
    <article className="rounded-card border border-line bg-gradient-to-br from-wash to-transparent p-4 shadow-card sm:p-5">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Badge tone={status.tone}>{status.label}</Badge>
        {matched && (
          <Badge tone="dim" className="max-w-full">
            <span className="max-w-[52vw] truncate sm:max-w-[360px]">
              Độ khớp {matched.percent}% · {matched.question}
            </span>
          </Badge>
        )}
        {answer.score != null && !matched && (
          <Badge tone="dim">điểm {Math.round(answer.score * 100)}%</Badge>
        )}
      </div>

      <p className="m-0 whitespace-pre-wrap text-[15px] leading-[1.78] text-content">
        {answer.text}
      </p>

      {answer.candidates?.length > 0 && (
        <div className="mt-4 rounded-xl border border-line bg-wash p-3">
          <p className="m-0 mb-2 text-[10px] font-semibold tracking-[0.12em] text-faint uppercase">
            Có phải bạn hỏi
          </p>
          <div className="flex flex-wrap gap-1.5">
            {answer.candidates.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => onPick?.(item.question)}
                className="inline-flex min-h-11 max-w-full items-center gap-2 rounded-lg border border-line bg-wash-strong px-2.5 py-1.5 text-left text-[11.5px] text-dim transition hover:bg-wash-hover hover:text-content focus-ring sm:min-h-0"
              >
                <span className="min-w-0 truncate">{item.question}</span>
                <span className="shrink-0 font-mono text-[10.5px] text-faint">
                  {item.percent}%
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-1.5">
        {playing ? (
          <button
            type="button"
            onClick={onStop}
            aria-pressed="true"
            aria-label="Đang đọc — bấm để dừng"
            title="Bấm để dừng"
            className="inline-flex min-h-11 max-w-full items-center gap-2 rounded-control border border-accent/40 bg-accent/10 px-2.5 py-1.5 text-[11.5px] font-semibold text-accent transition hover:bg-accent/15 focus-ring sm:min-h-0"
          >
            <span
              className="h-2 w-2 shrink-0 animate-pulse rounded-full bg-current motion-reduce:animate-none"
              aria-hidden="true"
            />
            <span className="shrink-0">Đang đọc</span>
            <span
              className="h-1.5 w-16 shrink-0 overflow-hidden rounded-full bg-track sm:w-24"
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
            <span className="shrink-0 font-mono text-[10.5px] tabular-nums">
              {timing}
            </span>
          </button>
        ) : (
          <Button variant="secondary" size="sm" onClick={onRead} disabled={!answer.text}>
            <SpeakerIcon />
            Đọc
          </Button>
        )}

        <button
          type="button"
          onClick={copy}
          className="inline-flex min-h-11 items-center gap-1.5 rounded-lg px-2 py-1 text-[11.5px] text-faint transition hover:bg-wash-hover hover:text-content focus-ring sm:min-h-0"
          aria-label="Sao chép câu trả lời"
        >
          <CopyIcon />
          {copied ? "Đã chép" : "Sao chép"}
        </button>

        {downloadUrl && (
          <a
            href={downloadUrl}
            download
            className="ml-auto inline-flex min-h-11 items-center gap-1.5 rounded-lg px-2 py-1 text-[11.5px] text-accent transition hover:bg-accent/10 focus-ring sm:min-h-0"
          >
            <DownloadIcon />
            Tải WAV
          </a>
        )}
      </div>
    </article>
  );
}
