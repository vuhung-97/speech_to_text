// Sticky "what is being read" strip: identifies the answer and offers stop.

import Button from "../../components/ui/Button";

export default function ReadingNow({ turn, speech, audioPlaying, onStop }) {
  if (!turn) return null;

  const active = speech.busy || audioPlaying;
  const progress = Math.round((speech.progress || 0) * 100);

  return (
    <div
      role="status"
      aria-live="polite"
      className="shrink-0 border-t border-line bg-accent/[0.05] px-5 py-2.5"
    >
      <div className="mx-auto flex max-w-[760px] items-center gap-3">
        <span
          className={`h-2.5 w-2.5 shrink-0 rounded-full ${
            active ? "animate-pulse bg-accent motion-reduce:animate-none" : "bg-faint"
          }`}
          aria-hidden="true"
        />

        <div className="min-w-0 flex-1">
          <p className="m-0 text-[12px] font-semibold tracking-[0.06em] text-accent uppercase">
            Đang đọc
          </p>
          <p
            className="m-0 truncate text-[13px] text-white"
            title={turn.answer?.text || ""}
          >
            {turn.answer?.text}
          </p>
          <div className="mt-1 h-1 overflow-hidden rounded-full bg-white/10">
            {speech.estimated ? (
              <div
                className="h-full rounded-full bg-gradient-to-r from-accent to-accent-2"
                style={{ width: `${progress}%` }}
              />
            ) : (
              <div className="h-full w-1/3 animate-pulse rounded-full bg-accent/60 motion-reduce:animate-none" />
            )}
          </div>
        </div>

        {speech.estimated > 0 && (
          <span className="shrink-0 font-mono text-[12px] text-faint">
            {speech.seconds.toFixed(1)}s
          </span>
        )}
        <Button variant="danger" size="sm" onClick={onStop}>
          Dừng
        </Button>
      </div>
    </div>
  );
}
