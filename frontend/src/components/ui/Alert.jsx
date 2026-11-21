// Inline message block used by every screen. One definition of the error
// colour/padding instead of the same Tailwind string repeated per page.

const TONES = {
  err: "border-err/35 bg-err/10 text-err",
  accent: "border-accent/35 bg-accent/10 text-accent",
  note: "border-accent/30 bg-accent/[0.08] text-accent",
};

const SIZES = {
  md: "px-3 py-2 text-[12px]",
  compact: "px-3 py-1.5 text-[12px]",
  sm: "px-2 py-1.5 text-[12px] leading-relaxed",
};

export default function Alert({
  tone = "err",
  size = "md",
  className = "",
  role,
  children,
}) {
  return (
    <p
      role={role ?? (tone === "err" ? "alert" : undefined)}
      className={`rounded-lg border ${SIZES[size] || SIZES.md} ${
        TONES[tone] || TONES.err
      } ${className}`}
    >
      {children}
    </p>
  );
}
