// Composition of the app-wide providers. Order matters: Toast is used by the
// other two, and Settings reads the live snapshot from Live.

import { LiveProvider } from "../shared/live/LiveProvider";
import { ThemeProvider } from "../shared/ui/ThemeProvider";
import { VoiceProvider } from "../shared/tts/VoiceProvider";
import { ToastProvider } from "../shared/ui/ToastProvider";
import { SettingsProvider } from "../features/settings";

export function AppProviders({ children }) {
  return (
    <ThemeProvider>
      <ToastProvider>
        <LiveProvider>
          <VoiceProvider>
            <SettingsProvider>{children}</SettingsProvider>
          </VoiceProvider>
        </LiveProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}
