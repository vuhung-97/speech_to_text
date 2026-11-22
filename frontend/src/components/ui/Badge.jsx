const TONES = {
  accent: "border-accent/35 bg-accent/12 text-accent",
  ok: "border-ok/35 bg-ok/10 text-ok",
  err: "border-err/35 bg-err/10 text-err",
  dim: "border-line bg-wash-strong text-dim",
  neutral: "border-line bg-wash text-faint",
};

export default function Badge({ tone = "dim", className = "", title, children }) {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[12px] leading-none ${TONES[tone] || TONES.dim} ${className}`}
    >
      {children}
    </span>
  );
}
