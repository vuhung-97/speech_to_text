// Square icon-only button. `label` is required so every control has a name.

export default function IconButton({
  label,
  active = false,
  className = "",
  type = "button",
  children,
  ...rest
}) {
  return (
    <button
      type={type}
      aria-label={label}
      title={label}
      aria-pressed={active || undefined}
      className={`grid h-11 w-11 place-items-center rounded-control border transition active:bg-white/[0.06] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:h-9 sm:w-9 ${
        active
          ? "border-accent/40 bg-accent/15 text-accent"
          : "border-line bg-white/[0.03] text-dim hover:bg-white/[0.075] hover:text-white"
      } ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
