// Backwards-compatible facade over the three focused providers.
//
// Screens still call `useApp()` while the codebase migrates to `useLive`,
// `useSettings` and `useToast`. Remove this facade in P4 once every component
// imports the context it actually needs.

import { useMemo } from "react";

import { useToast } from "../app/ToastProvider";
import { useLive } from "../features/dictation/LiveProvider";
import { useSettings } from "../features/settings/SettingsProvider";

export function useApp() {
  const toast = useToast();
  const live = useLive();
  const settings = useSettings();
  return useMemo(() => ({ ...toast, ...live, ...settings }), [toast, live, settings]);
}
