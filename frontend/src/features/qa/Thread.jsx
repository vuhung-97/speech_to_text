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
      className="mx-auto flex max-w-[720px] flex-col gap-5"
      aria-busy="true"
      aria-label="Đang tải phiên hội thoại"
    >
      {[0, 1, 2].map((item) => (
        <div key={item} className="animate-pulse space-y-2.5 motion-reduce:animate-none">
          <div className="ml-auto h-10 w-2/3 rounded-card bg-white/[0.05]" />
          <div className="h-16 rounded-card bg-white/[0.04]" />
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
      className="scroll-thin min-h-0 flex-1 overflow-y-auto px-5 py-5"
    >
      {loading && turns.length === 0 ? (
        <ThreadSkeleton />
      ) : turns.length === 0 ? (
        <div className="mx-auto max-w-[640px]">
          <EmptyState
            title="Bắt đầu hỏi"
            hint="Nói hoặc gõ câu hỏi; câu trả lời lấy nguyên văn từ kho."
            action={
              <div className="flex flex-wrap justify-center gap-1.5">
                {EXAMPLES.map((example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => onExample?.(example)}
                    className="inline-flex min-h-11 items-center rounded-lg border border-line bg-white/[0.04] px-2.5 py-1.5 text-[12px] text-dim transition hover:bg-white/[0.08] hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:min-h-0"
                  >
                    {example}
                  </button>
                ))}
              </div>
            }
          />
        </div>
      ) : (
        <div className="mx-auto flex max-w-[720px] flex-col gap-5" aria-live="polite">
          {turns.map((turn) => (
            <TurnCard
              key={turn.id}
              turn={turn}
              {...(renderAnswerProps ? renderAnswerProps(turn) : {})}
            />
          ))}
        </div>
      )}
    </div>
  );
}
