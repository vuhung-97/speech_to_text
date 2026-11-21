// Product shell: rail + topbar + content + optional evidence panel.
//
// Every screen renders inside it, so navigation, status and global shortcuts
// (Ctrl+K, Ctrl+Comma) exist in exactly one place.

import { useEffect, useRef, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";

import { useLive } from "../shared/live/LiveProvider";
import BrandMark from "../components/BrandMark";
import CommandPalette from "../components/CommandPalette";
import IconButton from "../components/ui/IconButton";
import SettingsDrawer from "../features/settings";
import StatusPill from "../components/StatusPill";

const ICONS = {
  ask: "M21 15a3 3 0 0 1-3 3H8l-5 3V6a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3z",
  sessions: "M4 6h16M4 12h16M4 18h10",
  faq: "M4 5h16v14H4zM8 9h8M8 13h5",
  mic: "M12 3a3 3 0 0 1 3 3v6a3 3 0 1 1-6 0V6a3 3 0 0 1 3-3zM5 11a7 7 0 0 0 14 0M12 18v3",
  settings:
    "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z",
  panel: "M4 4h16v16H4zM14 4v16M7 8h4M7 12h4",
  command: "M9 6a3 3 0 1 0-3 3h12a3 3 0 1 0-3-3v12a3 3 0 1 0 3-3H6a3 3 0 1 0 3 3z",
};

const NAV = [
  { to: "/", icon: "ask", label: "Hỏi đáp", end: true },
  { to: "/sessions", icon: "sessions", label: "Phiên" },
  { to: "/faq", icon: "faq", label: "Kho hỏi" },
  { to: "/dictation", icon: "mic", label: "Chính tả" },
  { to: "/settings", icon: "settings", label: "Cài đặt" },
];

function NavIcon({ name }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-[19px] w-[19px]"
      aria-hidden="true"
    >
      <path d={ICONS[name]} />
    </svg>
  );
}

export default function AppShell({ title, subtitle, right = null, actions = null, children }) {
  const { status } = useLive();
  const location = useLocation();
  const mainRef = useRef(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);

  useEffect(() => {
    mainRef.current?.focus();
  }, [location.pathname]);

  useEffect(() => {
    const onKey = (event) => {
      const mod = event.ctrlKey || event.metaKey;
      if (mod && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((open) => !open);
      } else if (mod && event.key === ",") {
        event.preventDefault();
        setSettingsOpen((open) => !open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className={status.paused ? "paused flex h-dvh" : "flex h-dvh"}>
      <nav
        aria-label="Điều hướng chính"
        className="flex w-[74px] shrink-0 flex-col items-center gap-1 border-r border-line bg-surface/70 py-4"
      >
        <BrandMark className="mb-3 h-9 w-9 shadow-accent" />

        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `flex w-[62px] flex-col items-center gap-1 rounded-xl px-1 py-2 text-[12px] transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
                isActive
                  ? "bg-accent/15 text-accent"
                  : "text-faint hover:bg-white/[0.05] hover:text-white"
              }`
            }
          >
            <NavIcon name={item.icon} />
            <span className="leading-none">{item.label}</span>
          </NavLink>
        ))}

        <span className="mt-auto text-[12px] tracking-[0.08em] text-faint">
          BETA
        </span>
      </nav>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-line px-5">
          <div className="min-w-0">
            <h1 className="m-0 truncate text-[14px] font-semibold tracking-tight">
              {title}
            </h1>
            {subtitle && (
              <p className="m-0 truncate text-[12px] text-faint">{subtitle}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {actions}
            <StatusPill />
            <IconButton
              label="Điều hướng nhanh (Ctrl+K)"
              onClick={() => setPaletteOpen(true)}
            >
              <NavIcon name="command" />
            </IconButton>
            {right && (
              <IconButton
                label={panelOpen ? "Ẩn bảng phụ" : "Hiện bảng phụ"}
                active={panelOpen}
                onClick={() => setPanelOpen((open) => !open)}
                className="max-xl:hidden"
              >
                <NavIcon name="panel" />
              </IconButton>
            )}
            <IconButton
              label="Cài đặt (Ctrl+Comma)"
              onClick={() => setSettingsOpen(true)}
            >
              <NavIcon name="settings" />
            </IconButton>
          </div>
        </header>

        <div className="flex min-h-0 flex-1">
          <main
            ref={mainRef}
            tabIndex={-1}
            className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden outline-none"
          >
            {children}
          </main>
          {right && (
            <aside
              aria-label="Bảng phụ"
              className={`scroll-thin w-[320px] shrink-0 overflow-y-auto border-l border-line bg-surface/40 px-4 py-4 max-xl:hidden ${
                panelOpen ? "" : "xl:hidden"
              }`}
            >
              {right}
            </aside>
          )}
        </div>
      </div>

      <SettingsDrawer open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}
