// Right-side drawer shell: overlay, panel, header, scroll body and footer.
// One owner for Esc, focus trap and focus return keeps every drawer usable
// with the keyboard without repeating the behaviour per screen.

import { useEffect, useRef } from "react";

import IconButton from "./IconButton";

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), ' +
  'input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

function CloseIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4"
      aria-hidden="true"
    >
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  );
}

export default function Drawer({
  open,
  onClose,
  label,
  title,
  subtitle = null,
  width = "w-[min(430px,100vw)]",
  headerClass = "items-center px-5 py-3.5",
  contentClass = "p-5",
  footer = null,
  children,
}) {
  const panelRef = useRef(null);
  const triggerRef = useRef(null);
  const closeRef = useRef(onClose);

  useEffect(() => {
    closeRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) return undefined;

    triggerRef.current = document.activeElement;
    const panel = panelRef.current;

    const onKey = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeRef.current();
        return;
      }
      if (event.key !== "Tab") return;

      const items = Array.from(panel?.querySelectorAll(FOCUSABLE) || []);
      if (!items.length) {
        event.preventDefault();
        panel?.focus();
        return;
      }
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKey);
    const timer = window.setTimeout(() => {
      const target =
        panel?.querySelector("[data-autofocus]") ||
        panel?.querySelector(FOCUSABLE) ||
        panel;
      target?.focus();
    }, 20);

    return () => {
      document.removeEventListener("keydown", onKey);
      window.clearTimeout(timer);
      const trigger = triggerRef.current;
      if (trigger instanceof HTMLElement && trigger.isConnected) trigger.focus();
    };
  }, [open]);

  return (
    <>
      <div
        onClick={onClose}
        className={`fixed inset-0 z-40 bg-black/55 backdrop-blur-[2px] transition-opacity motion-reduce:transition-none ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        aria-hidden="true"
      />

      <aside
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={label}
        aria-hidden={!open}
        inert={!open}
        tabIndex={-1}
        className={`fixed top-0 right-0 z-50 flex h-dvh ${width} flex-col border-l border-line bg-gradient-to-b from-surface-2 to-[#0d1014] shadow-[-40px_0_90px_-40px_#000] outline-none transition-transform duration-200 motion-reduce:transition-none ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <header className={`flex justify-between gap-3 border-b border-line ${headerClass}`}>
          <div className="min-w-0">
            <h2 className="m-0 flex items-center gap-2 text-[15px] font-semibold">
              {title}
            </h2>
            {subtitle && (
              <p className="mt-1 mb-0 text-[12px] text-faint">{subtitle}</p>
            )}
          </div>
          <IconButton label="Đóng" onClick={onClose}>
            <CloseIcon />
          </IconButton>
        </header>

        <div
          className={`scroll-thin flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto ${contentClass}`}
        >
          {children}
        </div>

        {footer && <footer className="border-t border-line px-5 py-3">{footer}</footer>}
      </aside>
    </>
  );
}
