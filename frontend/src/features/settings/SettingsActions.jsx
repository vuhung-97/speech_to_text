import { useSettings } from "./SettingsProvider";

export default function SettingsActions() {
  const { dirty, applyDirty, resetSettings } = useSettings();
  const dirtyCount = Object.keys(dirty).length;

  return (
    <div className="flex flex-wrap items-center gap-2.5">
      <button
        type="button"
        onClick={applyDirty}
        disabled={dirtyCount === 0}
        className="min-h-11 rounded-xl bg-gradient-to-br from-accent to-accent-2 px-4 py-2 text-[13.5px] font-semibold text-on-accent transition hover:brightness-110 focus-ring disabled:cursor-default disabled:opacity-45 sm:min-h-0"
      >
        Áp dụng
      </button>
      <button
        type="button"
        onClick={resetSettings}
        className="min-h-11 rounded-xl px-3 py-2 text-[13.5px] text-dim hover:bg-wash-hover hover:text-content focus-ring sm:min-h-0"
      >
        Mặc định
      </button>
      {dirtyCount > 0 && (
        <span className="min-w-full flex-1 text-left text-[12px] text-faint sm:min-w-0 sm:text-right">
          {dirtyCount} thay đổi
        </span>
      )}
    </div>
  );
}
