const TONES = {
  accent: "border-accent/35 bg-accent/12 text-accent",
  ok: "border-ok/35 bg-ok/10 text-ok",
  err: "border-err/35 bg-err/10 text-err",
  dim: "border-line bg-white/[0.04] text-dim",
  neutral: "border-line bg-white/[0.02] text-faint",
};

export default function Badge({ tone = "dim", className = "", children }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] leading-none ${TONES[tone] || TONES.dim} ${className}`}
    >
      {children}
    </span>
  );
}
