// Shared empty/zero state: icon, one-line promise, one next action.

export default function EmptyState({ icon = null, title, hint, action = null }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-card border border-line bg-surface px-6 py-12 text-center">
      {icon && (
        <span className="mb-1 grid h-12 w-12 place-items-center rounded-full border border-accent/30 bg-accent/10 text-accent">
          {icon}
        </span>
      )}
      <p className="m-0 text-[14px] font-semibold">{title}</p>
      {hint && (
        <p className="m-0 max-w-[460px] text-[12.5px] leading-relaxed text-faint">
          {hint}
        </p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
