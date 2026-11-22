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
      className={`grid h-11 w-11 place-items-center rounded-control border transition active:bg-wash-hover focus-ring sm:h-9 sm:w-9 ${
        active
          ? "border-accent/40 bg-accent/15 text-accent"
          : "border-line bg-wash-strong text-dim hover:bg-wash-hover hover:text-content"
      } ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
