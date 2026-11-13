// One turn: the question as heard plus the answer it produced.

import AnswerCard from "./AnswerCard";

function timeLabel(value) {
  if (!value) return "";
  try {
    return new Date(value * 1000).toLocaleTimeString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

export default function TurnCard({ turn, ...answerProps }) {
  const { answer, question } = turn;

  return (
    <article className="space-y-2.5">
      <div className="flex justify-end">
        <div className="max-w-[88%] rounded-card rounded-br-md border border-accent/25 bg-accent/10 px-4 py-2.5">
          <p className="m-0 text-[14px] leading-relaxed text-white">{question}</p>
          <p className="m-0 mt-1 text-right text-[10.5px] text-faint">
            {turn.source === "typed" ? "gõ tay" : "giọng nói"} · {timeLabel(turn.created_at)}
          </p>
        </div>
      </div>

      {answer ? (
        <AnswerCard answer={answer} {...answerProps} />
      ) : (
        <div className="rounded-card border border-line bg-surface-2/40 px-4 py-3 text-[12.5px] text-faint">
          Chưa có câu trả lời.
        </div>
      )}
    </article>
  );
}
