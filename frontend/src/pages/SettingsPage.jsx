// Settings route: the same schema-driven form as the drawer, inline for deep links.

import AppShell from "../app/AppShell";
import SettingsActions from "../features/settings/SettingsActions";
import SettingsForm from "../features/settings/SettingsForm";

export default function SettingsPage() {
  return (
    <AppShell title="Cài đặt" subtitle="Model, micro, nhận dạng và giọng đọc">
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-5 py-6">
        <div className="mx-auto max-w-[720px]">
          <div className="rounded-card border border-line bg-surface-2/60 p-5">
            <SettingsForm />
            <div className="mt-5 border-t border-white/5 pt-4">
              <SettingsActions />
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
