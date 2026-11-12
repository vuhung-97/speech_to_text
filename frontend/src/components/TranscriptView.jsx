import { useEffect, useRef } from "react";

import { useApp } from "../context/AppContext";

function EmptyState() {
  return (
    <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-1 p-6 text-center">
      <span className="mb-3 grid h-14 w-14 place-items-center rounded-full border border-accent/30 bg-accent/10 text-accent">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-6 w-6"
        >
          <rect x="9" y="2" width="6" height="12" rx="3" />
          <path d="M5 10v1a7 7 0 0 0 14 0v-1M12 18v4" />
        </svg>
      </span>
      <p className="m-0 text-base font-semibold">Sẵn sàng nghe</p>
      <p className="m-0 text-[13.5px] text-faint">
        Nói tiếng Việt — chữ sẽ hiện khi chốt câu.
      </p>
    </div>
  );
}

export default function TranscriptView() {
  const { transcript, live, speaking, status } = useApp();
  const scroller = useRef(null);
  const pinned = useRef(true);
  const hasLive = Boolean(live.stable || live.tentative);
  const hasContent = transcript.paragraphs.length > 0 || hasLive;

  useEffect(() => {
    if (pinned.current && scroller.current) {
      scroller.current.scrollTop = scroller.current.scrollHeight;
    }
  }, [transcript, live, speaking]);

  const onScroll = () => {
    const element = scroller.current;
    if (!element) return;
    pinned.current =
      element.scrollHeight - element.scrollTop - element.clientHeight < 60;
  };

  const showLive = hasLive || (speaking && !status.paused);

  return (
    <div
      ref={scroller}
      onScroll={onScroll}
      className="scroll-thin relative min-h-0 flex-1 overflow-y-auto px-8 pt-7 pb-5"
    >
      {!hasContent && !speaking && <EmptyState />}

      <div role="log" aria-live="polite" aria-atomic="false" className="space-y-3">
        {transcript.paragraphs.map((paragraph) => (
          <p key={paragraph.id} className="transcript-text m-0 text-white">
            {paragraph.text}
          </p>
        ))}
      </div>

      {showLive && (
        <p className="transcript-text m-0 mt-3" aria-hidden="true">
          <span className="text-white">{live.stable}</span>
          {live.tentative && (
            <span className="text-dim"> {live.tentative}</span>
          )}
          <span className="caret" />
        </p>
      )}
    </div>
  );
}
