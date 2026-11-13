// Composition of the app-wide providers. Order matters: Toast is used by the
// other two, and Settings reads the live snapshot from Live.

import { ToastProvider } from "./ToastProvider";
import { LiveProvider } from "../features/dictation/LiveProvider";
import { SettingsProvider } from "../features/settings/SettingsProvider";

export function AppProviders({ children }) {
  return (
    <ToastProvider>
      <LiveProvider>
        <SettingsProvider>{children}</SettingsProvider>
      </LiveProvider>
    </ToastProvider>
  );
}
