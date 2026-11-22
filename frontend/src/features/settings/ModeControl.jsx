// Recognition mode control shown in the Q&A sidebar (moved out of Settings).

import { useSettings } from "./SettingsProvider";

const LABELS = {
  accurate: "Chính xác",
  realtime: "Realtime",
};

export default function ModeControl() {
  const { settings, dirty, setField } = useSettings();
  const field = (settings.fields || []).find((item) => item.key === "mode");
  const value = dirty.mode ?? settings.values.mode;

  return (
    <section className="rounded-xl border border-line bg-white/[0.02] p-3">
      <h2 className="m-0 mb-2 text-[12px] font-semibold tracking-[0.08em] text-faint uppercase">
        Chế độ
      </h2>

      {!field ? (
        <p className="m-0 text-[12px] text-faint">Đang tải…</p>
      ) : (
        <div
          role="group"
          aria-label="Chế độ nhận dạng"
          className="grid grid-cols-2 gap-1 rounded-lg border border-line bg-white/[0.03] p-1"
        >
          {field.options.map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={value === option}
              onClick={() => setField(field, option)}
              className={`min-h-11 rounded-md px-2 py-1.5 text-[12px] transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:min-h-0 ${
                value === option
                  ? "bg-accent/20 text-accent"
                  : "text-dim hover:bg-white/[0.06] hover:text-white"
              }`}
            >
              {LABELS[option] || option}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
