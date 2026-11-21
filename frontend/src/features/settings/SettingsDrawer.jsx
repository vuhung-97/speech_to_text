import { useLive } from "../../shared/live/LiveProvider";
import SettingsActions from "./SettingsActions";
import SettingsForm from "./SettingsForm";

export default function SettingsDrawer({ open, onClose }) {
  const { engine } = useLive();

  return (
    <>
      <div
        onClick={onClose}
        className={`fixed inset-0 z-40 bg-black/55 backdrop-blur-[2px] transition-opacity ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        aria-hidden="true"
      />

      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Cài đặt"
        aria-hidden={!open}
        inert={open ? undefined : ""}
        className={`fixed top-0 right-0 z-50 flex h-dvh w-[min(430px,100vw)] flex-col border-l border-line bg-gradient-to-b from-surface-2 to-[#0d1014] shadow-[-40px_0_90px_-40px_#000] transition-transform duration-200 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <header className="flex items-center justify-between gap-3 border-b border-line px-5 py-3.5">
          <div>
            <h2 className="m-0 text-[15px] font-semibold">Cài đặt</h2>
            <p className="m-0 mt-0.5 font-mono text-[11px] text-faint">
              {engine.state === "loading"
                ? "đang nạp model…"
                : `${engine.model || "?"} · ${engine.cpu_threads ?? "?"} thread · ${
                    engine.compute_type || "int8"
                  }`}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng cài đặt"
            className="grid h-9 w-9 place-items-center rounded-xl border border-line bg-white/[0.03] text-dim hover:bg-white/[0.075] hover:text-white"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              className="h-4 w-4"
            >
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </header>

        <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-5 pt-3 pb-6">
          <SettingsForm />
        </div>

        <footer className="border-t border-line px-5 py-3">
          <SettingsActions />
        </footer>
      </aside>
    </>
  );
}
