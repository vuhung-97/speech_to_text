// Modal keyboard behaviour shared by drawers and the command palette:
// Esc dismisses, Tab/Shift+Tab stay inside, and focus returns to the trigger.

import { useEffect, useRef } from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), ' +
  'input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

const FOCUS_DELAY_MS = 20;

export function useFocusTrap(panelRef, active, onDismiss) {
  const triggerRef = useRef(null);
  const dismissRef = useRef(onDismiss);

  useEffect(() => {
    dismissRef.current = onDismiss;
  }, [onDismiss]);

  useEffect(() => {
    if (!active) return undefined;

    triggerRef.current = document.activeElement;
    const panel = panelRef.current;

    const onKey = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        dismissRef.current?.();
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
    }, FOCUS_DELAY_MS);

    return () => {
      document.removeEventListener("keydown", onKey);
      window.clearTimeout(timer);
      const trigger = triggerRef.current;
      if (trigger instanceof HTMLElement && trigger.isConnected) trigger.focus();
    };
  }, [active, panelRef]);
}

export default useFocusTrap;
