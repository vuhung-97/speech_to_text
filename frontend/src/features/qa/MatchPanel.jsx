import Badge from "../../components/ui/Badge";
import PanelSection from "./PanelSection";

export default function MatchPanel({ lastAnswer, onPick }) {
  return (
    <PanelSection title="Câu hỏi khớp">
      {lastAnswer?.matched ? (
        <div className="space-y-1.5">
          <p className="m-0 text-[12.5px] leading-relaxed text-white">
            {lastAnswer.matched.question}
          </p>
          <div className="flex items-center gap-1.5">
            <Badge tone="ok">{lastAnswer.matched.percent}%</Badge>
            {lastAnswer.matched.category && (
              <Badge tone="dim">{lastAnswer.matched.category}</Badge>
            )}
          </div>
        </div>
      ) : lastAnswer ? (
        <p className="m-0 text-[12px] leading-relaxed text-faint">
          Câu hỏi chưa có trong kho. Đã ghi vào danh sách “chưa trả lời” để bạn
          bổ sung ở trang Kho câu hỏi.
        </p>
      ) : (
        <p className="m-0 text-[12px] text-faint">
          Chưa có lượt hỏi nào trong phiên này.
        </p>
      )}

      {lastAnswer?.candidates?.length > 0 && (
        <div className="mt-2 space-y-1">
          {lastAnswer.candidates.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onPick?.(item.question)}
              className="block min-h-11 w-full truncate rounded-lg px-2 py-1 text-left text-[12px] text-dim transition hover:bg-white/[0.06] hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:min-h-0"
            >
              {item.question} · {item.percent}%
            </button>
          ))}
        </div>
      )}
    </PanelSection>
  );
}
