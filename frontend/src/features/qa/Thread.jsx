// Conversation thread with an honest empty state.

import { useEffect, useRef } from "react";

import EmptyState from "../../components/ui/EmptyState";
import TurnCard from "./TurnCard";

const EXAMPLES = [
  "Thủ đô Việt Nam là gì?",
  "Quy trình đăng ký gồm những bước nào?",
  "Hồ sơ cần chuẩn bị giấy tờ gì?",
];

export default function Thread({ turns, onExample, renderAnswerProps }) {
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
      {turns.length === 0 ? (
        <div className="mx-auto max-w-[640px]">
          <EmptyState
            title="Hỏi bằng giọng nói hoặc gõ tay"
            hint="Câu hỏi được khớp với kho câu trả lời soạn sẵn. Chưa khớp thì hệ thống gợi ý câu gần nhất và ghi lại để bạn bổ sung sau."
            action={
              <div className="flex flex-wrap justify-center gap-1.5">
                {EXAMPLES.map((example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => onExample?.(example)}
                    className="rounded-lg border border-line bg-white/[0.04] px-2.5 py-1.5 text-[12px] text-dim transition hover:bg-white/[0.08] hover:text-white"
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
