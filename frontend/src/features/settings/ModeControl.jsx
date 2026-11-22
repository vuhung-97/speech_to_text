// Recognition mode control shown in the Q&A tools panel (moved out of Settings).

import { useSettings } from "./SettingsProvider";

const LABELS = {
  accurate: "Chính xác",
  realtime: "Realtime",
};

function SegmentedMode({ field, value, setField }) {
  if (!field) {
    return <p className="m-0 text-[11px] text-faint">Đang tải…</p>;
  }

  return (
    <div
      role="group"
      aria-label="Chế độ nhận dạng"
      className="grid grid-cols-2 gap-0.5 rounded-xl border border-line bg-wash-strong p-1"
    >
      {field.options.map((option) => (
        <button
          key={option}
          type="button"
          aria-pressed={value === option}
          onClick={() => setField(field, option)}
          className={`min-h-11 rounded-lg px-2 py-1.5 text-[10.5px] transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:min-h-0 ${
            value === option
              ? "bg-accent/15 font-semibold text-accent shadow-[inset_0_0_0_1px_var(--color-accent-soft)]"
              : "text-faint hover:bg-wash-hover hover:text-content"
          }`}
        >
          {LABELS[option] || option}
        </button>
      ))}
    </div>
  );
}

export default function ModeControl({ bare = false }) {
  const { settings, dirty, setField } = useSettings();
  const field = (settings.fields || []).find((item) => item.key === "mode");
  const value = dirty.mode ?? settings.values.mode;

  if (bare) {
    return (
      <div className="mb-2">
        <span className="mb-1 block text-[10.5px] text-faint">Chế độ</span>
        <SegmentedMode field={field} value={value} setField={setField} />
      </div>
    );
  }

  return (
    <section className="rounded-xl border border-line bg-wash p-3">
      <h2 className="m-0 mb-2 text-[12px] font-semibold tracking-[0.08em] text-faint uppercase">
        Chế độ
      </h2>
      <SegmentedMode field={field} value={value} setField={setField} />
    </section>
  );
}
