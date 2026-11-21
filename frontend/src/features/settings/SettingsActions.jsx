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
        className="min-h-11 rounded-xl bg-gradient-to-br from-accent to-accent-2 px-4 py-2 text-[13.5px] font-semibold text-[#201505] transition hover:brightness-110 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-default disabled:opacity-45 sm:min-h-0"
      >
        Áp dụng &amp; nạp lại
      </button>
      <button
        type="button"
        onClick={resetSettings}
        className="min-h-11 rounded-xl px-3 py-2 text-[13.5px] text-dim hover:bg-white/5 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:min-h-0"
      >
        Mặc định
      </button>
      <span className="min-w-full flex-1 text-left text-[12px] text-faint sm:min-w-0 sm:text-right">
        {dirtyCount ? `${dirtyCount} thay đổi cần nạp lại` : "Đổi trực tiếp là áp dụng ngay"}
      </span>
    </div>
  );
}
