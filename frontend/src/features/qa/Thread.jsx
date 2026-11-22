// Conversation thread with an honest empty state.

import { useEffect, useRef } from "react";

import EmptyState from "../../components/ui/EmptyState";
import TurnCard from "./TurnCard";

const EXAMPLES = [
  "Thủ đô Việt Nam là gì?",
  "Quy trình đăng ký gồm những bước nào?",
  "Hồ sơ cần chuẩn bị giấy tờ gì?",
];

function ThreadSkeleton() {
  return (
    <div
      className="mx-auto flex w-full max-w-[780px] flex-col gap-5"
      aria-busy="true"
      aria-label="Đang tải phiên hội thoại"
    >
      {[0, 1, 2].map((item) => (
        <div key={item} className="animate-pulse space-y-2.5 motion-reduce:animate-none">
          <div className="ml-auto h-10 w-2/3 rounded-card bg-wash-hover" />
          <div className="h-16 rounded-card bg-wash-strong" />
        </div>
      ))}
    </div>
  );
}

export default function Thread({ turns, loading = false, onExample, renderAnswerProps }) {
  const scroller = useRef(null);
  const pinned = useRef(true);

  useEffect(() => {
    if (pinned.current && scroller.current) {
      scroller.current.scrollTop = scroller.current.scrollHeight;
    }
  }, [turns]);

  return (
    <div
      ref={scroller}
      onScroll={() => {
        const element = scroller.current;
        if (!element) return;
        pinned.current =
          element.scrollHeight - element.scrollTop - element.clientHeight < 80;
      }}
      className="scroll-thin min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6 lg:px-8"
    >
      {loading && turns.length === 0 ? (
        <ThreadSkeleton />
      ) : turns.length === 0 ? (
        <div className="mx-auto max-w-[680px] pt-4">
          <EmptyState
            title="Hỏi nhanh, nghe đáp án"
            hint="Nói hoặc gõ câu hỏi. Câu trả lời được lấy nguyên văn từ kho offline trên máy."
            action={
              <div className="flex flex-wrap justify-center gap-1.5">
                {EXAMPLES.map((example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => onExample?.(example)}
                    className="inline-flex min-h-11 items-center rounded-full border border-line bg-wash-strong px-3 py-1.5 text-[12px] text-dim transition hover:bg-wash-hover hover:text-content focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:min-h-0"
                  >
                    {example}
                  </button>
                ))}
              </div>
            }
          />
        </div>
      ) : (
        <div className="mx-auto w-full max-w-[780px]" aria-live="polite">
          <div className="mb-4 flex items-center justify-between gap-3 text-[11px] text-faint">
            <span className="inline-flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-accent shadow-[0_0_10px_rgba(255,180,84,0.6)]" />
              Phiên hiện tại
            </span>
            <span>{turns.length} lượt</span>
          </div>
          <div className="flex flex-col gap-5">
            {turns.map((turn) => (
              <TurnCard
                key={turn.id}
                turn={turn}
                {...(renderAnswerProps ? renderAnswerProps(turn) : {})}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
