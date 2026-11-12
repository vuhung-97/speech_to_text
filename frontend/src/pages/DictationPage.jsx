import { useEffect, useState } from "react";

import LevelMeter from "../components/LevelMeter";
import ControlsBar from "../components/ControlsBar";
import SettingsDrawer from "../components/SettingsDrawer";
import StatusPill from "../components/StatusPill";
import TranscriptView from "../components/TranscriptView";
import { useApp } from "../context/AppContext";

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <span className="grid h-[38px] w-[38px] place-items-center rounded-xl bg-gradient-to-br from-accent to-accent-2 text-[#1a1206] shadow-[0_10px_24px_-12px_rgba(255,138,61,0.9)]">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-[19px] w-[19px]"
        >
          <rect x="9" y="2" width="6" height="12" rx="3" />
          <path d="M5 10v1a7 7 0 0 0 14 0v-1M12 18v4" />
        </svg>
      </span>
      <div>
        <h1 className="m-0 text-base font-semibold tracking-tight">STT Trực Tiếp</h1>
        <p className="m-0 mt-px text-[11.5px] tracking-[0.04em] text-faint uppercase max-sm:hidden">
          zipformer · offline · realtime
        </p>
      </div>
    </div>
  );
}

export default function DictationPage() {
  const { status, togglePause } = useApp();
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    const onKeyDown = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === ",") {
        event.preventDefault();
        setDrawerOpen((open) => !open);
        return;
      }
      if (event.key !== "Escape" || event.ctrlKey || event.altKey || event.metaKey) {
        return;
      }
      event.preventDefault();
      if (drawerOpen) setDrawerOpen(false);
      else togglePause();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [drawerOpen, togglePause]);

  return (
    <div className={status.paused ? "paused" : ""}>
      <div
        className="pointer-events-none fixed inset-x-0 -top-[30%] h-[60vh] bg-[radial-gradient(60%_100%_at_50%_100%,rgba(255,180,84,0.10),transparent_70%)]"
        aria-hidden="true"
      />
      <div className="relative mx-auto flex h-dvh max-w-[940px] flex-col gap-4 px-6 pt-6 pb-4 max-sm:px-3.5 max-sm:pt-4">
        <header className="flex items-center justify-between gap-4">
          <Brand />
          <div className="flex items-center gap-2.5">
            <StatusPill />
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              aria-label="Cài đặt"
              title="Cài đặt (Ctrl+Comma)"
              className="grid h-9 w-9 place-items-center rounded-xl border border-line bg-white/[0.03] text-dim transition hover:bg-white/[0.075] hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="h-[18px] w-[18px]"
              >
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </button>
          </div>
        </header>

        <LevelMeter />

        <main className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[20px] border border-line bg-surface shadow-[0_40px_90px_-50px_#000]">
          <TranscriptView />
          <ControlsBar />
        </main>

        <p className="m-0 hidden text-center text-[12px] text-faint sm:block">
          Nghỉ ~0.6 giây để chốt câu · chữ mờ là bản nháp ·{" "}
          <kbd className="rounded border border-line bg-white/[0.04] px-1.5 py-px font-mono text-[10.5px] text-dim">
            Esc
          </kbd>{" "}
          tạm dừng / tiếp tục ·{" "}
          <kbd className="rounded border border-line bg-white/[0.04] px-1.5 py-px font-mono text-[10.5px] text-dim">
            Ctrl
          </kbd>
          +
          <kbd className="rounded border border-line bg-white/[0.04] px-1.5 py-px font-mono text-[10.5px] text-dim">
            ,
          </kbd>{" "}
          cài đặt
        </p>
      </div>

      <SettingsDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </div>
  );
}
