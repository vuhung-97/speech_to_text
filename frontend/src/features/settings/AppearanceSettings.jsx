// Theme preference in the settings drawer. The top bar has a one-click toggle;
// this panel names both choices explicitly.

import { useTheme } from "../../shared/ui/ThemeProvider";

const OPTIONS = [
  { id: "light", label: "Sáng" },
  { id: "dark", label: "Tối" },
];

export default function AppearanceSettings() {
  const { theme, setTheme } = useTheme();

  return (
    <section className="border-b border-line pb-3">
      <h3 className="mb-2 text-[12px] font-semibold tracking-[0.09em] text-faint uppercase">
        Giao diện
      </h3>
      <div
        role="group"
        aria-label="Giao diện"
        className="grid grid-cols-2 gap-1 rounded-xl border border-line bg-wash-strong p-1"
      >
        {OPTIONS.map((option) => (
          <button
            key={option.id}
            type="button"
            aria-pressed={theme === option.id}
            onClick={() => setTheme(option.id)}
            className={`min-h-11 rounded-lg px-2 py-1.5 text-[11.5px] transition focus-ring sm:min-h-0 ${
              theme === option.id
                ? "bg-accent/15 font-semibold text-accent"
                : "text-faint hover:bg-wash-hover hover:text-content"
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>
      <p className="mt-1.5 mb-0 text-[11px] leading-relaxed text-faint">
        Lựa chọn được lưu trên trình duyệt này.
      </p>
    </section>
  );
}
