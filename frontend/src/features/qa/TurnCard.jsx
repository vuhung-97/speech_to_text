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
        <div className="max-w-[88%] rounded-[18px] rounded-br-[6px] border border-accent/20 bg-accent/10 px-4 py-2.5 shadow-[0_12px_30px_-24px_var(--color-accent-2)]">
          <p className="m-0 text-[13.5px] leading-relaxed text-user-text">
            {question}
          </p>
          <p className="m-0 mt-1 text-right text-[10.5px] text-faint">
            {timeLabel(turn.created_at)}
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
