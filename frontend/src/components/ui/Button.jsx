// Minimal UI primitives. Screens compose these instead of repeating class
// strings; variants are the only visual decisions a screen makes.

const BASE =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-control font-medium transition " +
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent " +
  "disabled:cursor-default disabled:opacity-45 sm:min-h-0";

const VARIANTS = {
  primary:
    "bg-gradient-to-br from-accent to-accent-2 text-[#201505] hover:brightness-110",
  secondary:
    "border border-line bg-white/[0.04] text-dim hover:bg-white/[0.08] hover:text-white",
  ghost: "text-dim hover:bg-white/[0.06] hover:text-white",
  danger:
    "border border-err/35 bg-err/10 text-err hover:bg-err/15",
};

const SIZES = {
  sm: "px-2.5 py-1.5 text-[12px]",
  md: "px-3.5 py-2 text-[13px]",
  lg: "px-4 py-2.5 text-[13.5px]",
};

export default function Button({
  variant = "secondary",
  size = "md",
  className = "",
  type = "button",
  ...rest
}) {
  return (
    <button
      type={type}
      className={`${BASE} ${VARIANTS[variant] || VARIANTS.secondary} ${SIZES[size] || SIZES.md} ${className}`}
      {...rest}
    />
  );
}
