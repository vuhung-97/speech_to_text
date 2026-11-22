// Search field shared by the catalogue and the session history.
// One definition of the magnifier, the label and the input surface.

function SearchIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      aria-hidden="true"
      className="h-3.5 w-3.5 shrink-0 text-faint"
    >
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.4-3.4" />
    </svg>
  );
}

export default function SearchInput({
  label,
  value,
  onChange,
  placeholder,
  className = "",
  ...rest
}) {
  return (
    <label
      className={
        "flex min-h-11 min-w-0 items-center gap-2 rounded-control border border-line " +
        "bg-wash-strong px-3 py-2 focus-within:border-accent/60 sm:min-h-0 " +
        className
      }
    >
      <SearchIcon />
      <span className="sr-only">{label}</span>
      <input
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="w-full min-w-0 border-0 bg-transparent text-[12px] text-content outline-none placeholder:text-faint"
        {...rest}
      />
    </label>
  );
}
