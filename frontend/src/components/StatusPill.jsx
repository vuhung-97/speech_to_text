import { useLive } from "../features/dictation/LiveProvider";
import { STATUS_LABELS } from "../utils/format";

const DOT = {
  listening: "bg-accent shadow-[0_0_0_0_rgba(255,180,84,0.45)] animate-pulse",
  paused: "bg-accent-2",
  error: "bg-err",
  disconnected: "bg-err",
  connecting: "bg-faint",
};

export default function StatusPill({ state: overrideState, label }) {
  const { status } = useLive();
  const state = overrideState || status.state || "connecting";
  const text = label || STATUS_LABELS[state] || state;
  return (
    <div
      role="status"
      aria-live="polite"
      className={`inline-flex items-center gap-2.5 rounded-full border border-line bg-white/[0.03] px-3.5 py-1.5 text-[13px] whitespace-nowrap ${
        state === "error" ? "border-err/40 text-err" : "text-dim"
      }`}
    >
      <span className={`h-[7px] w-[7px] rounded-full ${DOT[state] || "bg-faint"}`} />
      <span className={state === "listening" ? "text-white" : ""}>
        {text}
      </span>
    </div>
  );
}
