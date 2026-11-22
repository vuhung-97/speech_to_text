// The product mark: one SVG definition shared by the app rail and the
// dictation header. Size/shadow come from the caller so each context keeps its
// exact scale.

export default function BrandMark({
  className = "h-9 w-9",
  iconClassName = "h-[18px] w-[18px]",
}) {
  return (
    <span
      className={`grid place-items-center rounded-xl bg-gradient-to-br from-accent to-accent-2 text-on-accent ${className}`}
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={iconClassName}
      >
        <rect x="9" y="2" width="6" height="12" rx="3" />
        <path d="M5 10v1a7 7 0 0 0 14 0v-1M12 18v4" />
      </svg>
    </span>
  );
}
