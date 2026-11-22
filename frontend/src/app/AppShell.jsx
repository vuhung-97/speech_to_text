// Product shell: rail + topbar + content + optional tools panel.
//
// Every screen renders inside it, so navigation, status, theme and global
// shortcuts (Ctrl+K, Ctrl+Comma) exist in exactly one place. Below lg the rail
// becomes a bottom navigation bar and the tools panel becomes a bottom sheet.

import { useEffect, useRef, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";

import { useLive } from "../shared/live/LiveProvider";
import BrandMark from "../components/BrandMark";
import CommandPalette from "../components/CommandPalette";
import IconButton from "../components/ui/IconButton";
import ThemeToggle from "../components/ui/ThemeToggle";
import { useFocusTrap } from "../components/ui/useFocusTrap";
import SettingsDrawer from "../features/settings";
import StatusPill from "../components/StatusPill";

const ICONS = {
  ask: "M21 15a3 3 0 0 1-3 3H8l-5 3V6a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3z",
  sessions: "M4 6h16M4 12h16M4 18h10",
  faq: "M4 5h16v14H4zM8 9h8M8 13h5",
  settings:
    "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z",
  panel: "M4 4h16v16H4zM14 4v16M7 8h4M7 12h4",
  command: "M9 6a3 3 0 1 0-3 3h12a3 3 0 1 0-3-3v12a3 3 0 1 0 3-3H6a3 3 0 1 0 3 3z",
  sliders: "M4 7h16M4 12h16M4 17h16M9 7v0M15 12v0M11 17v0",
};

const NAV = [
  { to: "/", icon: "ask", label: "Hỏi đáp", end: true },
  { to: "/sessions", icon: "sessions", label: "Phiên" },
  { to: "/faq", icon: "faq", label: "Kho hỏi" },
];

const NAV_ITEM_BASE =
  "transition focus-ring";

// One definition for the rail (desktop) and the bottom bar (mobile).
function navItemClass(isActive, compact = false) {
  if (compact) {
    return `flex min-w-0 flex-col items-center justify-center gap-1 text-[9.5px] ${NAV_ITEM_BASE} ${
      isActive ? "text-accent" : "text-faint hover:text-content"
    }`;
  }
  return `relative flex min-h-[58px] w-full flex-col items-center justify-center gap-1 rounded-xl px-1 py-2 text-[10.5px] ${NAV_ITEM_BASE} ${
    isActive
      ? "bg-accent/15 text-accent"
      : "text-faint hover:bg-wash-hover hover:text-content"
  }`;
}

function NavIcon({ name, className = "h-[19px] w-[19px]" }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d={ICONS[name]} />
    </svg>
  );
}

function MobileNav({ hasTools, toolsOpen, onTools, onSettings }) {
  return (
    <nav
      aria-label="Điều hướng di động"
      className="grid h-[58px] shrink-0 grid-cols-4 border-t border-line bg-surface/95 lg:hidden"
    >
      {NAV.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) => navItemClass(isActive, true)}
        >
          <NavIcon name={item.icon} className="h-[19px] w-[19px]" />
          <span className="truncate">{item.label}</span>
        </NavLink>
      ))}

      {hasTools ? (
        <button
          type="button"
          onClick={onTools}
          aria-expanded={toolsOpen}
          className={navItemClass(toolsOpen, true)}
        >
          <NavIcon name="sliders" className="h-[19px] w-[19px]" />
          <span>Công cụ</span>
        </button>
      ) : (
        <button
          type="button"
          onClick={onSettings}
          className={navItemClass(false, true)}
        >
          <NavIcon name="settings" className="h-[19px] w-[19px]" />
          <span>Cài đặt</span>
        </button>
      )}
    </nav>
  );
}

export default function AppShell({
  title,
  subtitle,
  right = null,
  rightTitle = "Công cụ",
  actions = null,
  children,
}) {
  const { status } = useLive();
  const location = useLocation();
  const mainRef = useRef(null);
  const toolsRef = useRef(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);
  const [toolsOpen, setToolsOpen] = useState(false);

  const openSettings = () => setSettingsOpen(true);
  const closeTools = () => setToolsOpen(false);
  useFocusTrap(toolsRef, toolsOpen, closeTools);

  useEffect(() => {
    mainRef.current?.focus();
    setToolsOpen(false);
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
    <div
      className={`${
        status.paused ? "paused " : ""
      }flex h-dvh flex-col overflow-hidden bg-ink lg:flex-row`}
    >
      <nav
        aria-label="Điều hướng chính"
        className="hidden w-[76px] shrink-0 flex-col items-center gap-1 border-r border-line bg-surface/70 py-4 lg:flex"
      >
        <BrandMark className="mb-4 h-10 w-10 shadow-accent" />

        <div className="flex w-full flex-col gap-1">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => navItemClass(isActive)}
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span
                      aria-hidden="true"
                      className="absolute top-4 bottom-4 left-0 w-0.5 rounded-full bg-accent shadow-[0_0_12px_rgba(255,180,84,0.55)]"
                    />
                  )}
                  <NavIcon name={item.icon} />
                  <span className="leading-none">{item.label}</span>
                </>
              )}
            </NavLink>
          ))}
        </div>
      </nav>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-line bg-surface/55 px-4 sm:px-5 lg:h-16 lg:px-6">
          <div className="min-w-0">
            <span className="mb-0.5 hidden text-[10px] font-semibold tracking-[0.13em] text-faint uppercase lg:block">
              Không gian làm việc
            </span>
            <h1 className="m-0 truncate text-[15px] font-semibold tracking-[-0.02em] lg:text-[17px]">
              {title}
            </h1>
            {subtitle && (
              <p className="m-0 truncate text-[11px] text-faint">{subtitle}</p>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-1.5">
            {actions}
            <StatusPill />
            <ThemeToggle />
            <IconButton
              label="Điều hướng nhanh (Ctrl+K)"
              onClick={() => setPaletteOpen(true)}
              className="hidden sm:grid"
            >
              <NavIcon name="command" className="h-4 w-4" />
            </IconButton>
            <IconButton label="Cài đặt (Ctrl+Comma)" onClick={openSettings}>
              <NavIcon name="settings" className="h-4 w-4" />
            </IconButton>
            {right && (
              <IconButton
                label={panelOpen ? "Ẩn bảng công cụ" : "Hiện bảng công cụ"}
                active={panelOpen}
                onClick={() => setPanelOpen((open) => !open)}
                className="hidden lg:grid"
              >
                <NavIcon name="panel" className="h-4 w-4" />
              </IconButton>
            )}
          </div>
        </header>

        <div className="flex min-h-0 flex-1">
          <main
            ref={mainRef}
            tabIndex={-1}
            className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-surface outline-none"
          >
            {children}
          </main>

          {right && (
            <>
              <div
                onClick={closeTools}
                aria-hidden="true"
                className={`fixed inset-0 z-40 bg-overlay transition-opacity duration-200 lg:hidden ${
                  toolsOpen ? "opacity-100" : "pointer-events-none opacity-0"
                }`}
              />

              <aside
                ref={toolsRef}
                tabIndex={-1}
                role={toolsOpen ? "dialog" : undefined}
                aria-modal={toolsOpen || undefined}
                aria-label={rightTitle}
                className={`scroll-thin shrink-0 overflow-y-auto bg-surface/40 px-4 py-4 outline-none max-lg:fixed max-lg:inset-x-2 max-lg:bottom-[64px] max-lg:z-50 max-lg:max-h-[72vh] max-lg:w-auto max-lg:rounded-2xl max-lg:border max-lg:border-line max-lg:bg-surface-2 max-lg:shadow-card lg:w-[326px] lg:border-l lg:border-line ${
                  panelOpen ? "lg:flex" : "lg:hidden"
                } ${toolsOpen ? "max-lg:flex" : "max-lg:hidden"} flex-col`}
              >
                <div className="mb-3 flex items-center justify-between gap-2">
                  <h2 className="m-0 text-[10.5px] font-semibold tracking-[0.13em] text-faint uppercase">
                    {rightTitle}
                  </h2>
                  <IconButton
                    label="Đóng bảng công cụ"
                    onClick={() => {
                      setPanelOpen(false);
                      setToolsOpen(false);
                    }}
                    className="h-11 w-11 border-transparent bg-transparent lg:h-8 lg:w-8"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      className="h-4 w-4"
                      aria-hidden="true"
                    >
                      <path d="M18 6 6 18M6 6l12 12" />
                    </svg>
                  </IconButton>
                </div>
                {right}
              </aside>
            </>
          )}
        </div>
      </div>

      <MobileNav
        hasTools={Boolean(right)}
        toolsOpen={toolsOpen}
        onTools={() => setToolsOpen((open) => !open)}
        onSettings={openSettings}
      />

      <SettingsDrawer open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}
