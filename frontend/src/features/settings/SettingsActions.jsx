import { useSettings } from "./SettingsProvider";

export default function SettingsActions() {
  const { dirty, applyDirty, resetSettings } = useSettings();
  const dirtyCount = Object.keys(dirty).length;

  return (
    <div className="flex items-center gap-2.5">
      <button
        type="button"
        onClick={applyDirty}
        disabled={dirtyCount === 0}
        className="rounded-xl bg-gradient-to-br from-accent to-accent-2 px-4 py-2 text-[13.5px] font-semibold text-[#201505] transition hover:brightness-110 disabled:cursor-default disabled:opacity-45"
      >
        Áp dụng &amp; nạp lại
      </button>
      <button
        type="button"
        onClick={resetSettings}
        className="rounded-xl px-3 py-2 text-[13.5px] text-dim hover:bg-white/5 hover:text-white"
      >
        Mặc định
      </button>
      <span className="flex-1 text-right text-[11px] text-faint">
        {dirtyCount ? `${dirtyCount} thay đổi cần nạp lại` : "Đổi trực tiếp là áp dụng ngay"}
      </span>
    </div>
  );
}
