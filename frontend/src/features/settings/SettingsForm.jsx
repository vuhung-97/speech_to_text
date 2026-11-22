// Settings body rendered inside the settings drawer (gear / Ctrl+,).
// One responsibility: render the schema-driven form and its side panels.

import { useLive } from "../../shared/live/LiveProvider";
import FieldRow from "./FieldRow";
import PresetPanel from "./PresetPanel";
import { useSettings } from "./SettingsProvider";

const GROUP_TITLES = {
  mode: "Chế độ",
  engine: "Model & tài nguyên",
  vad: "Câu & im lặng",
  stream: "Luồng (realtime)",
};

const GROUPS = ["mode", "engine", "vad", "stream"];

function EngineBadge({ engine }) {
  if (engine.state === "loading") {
    return (
      <span className="rounded-full border border-accent/40 bg-accent/10 px-2 py-0.5 text-[12px] tracking-wide text-accent normal-case">
        đang nạp…
      </span>
    );
  }
  if (engine.state === "error") {
    return (
      <span className="rounded-full border border-err/40 px-2 py-0.5 text-[12px] tracking-wide text-err normal-case">
        lỗi nạp
      </span>
    );
  }
  return (
    <span className="rounded-full border border-accent/40 bg-accent/10 px-2 py-0.5 text-[12px] tracking-wide text-accent normal-case">
      cần nạp lại khi đổi
    </span>
  );
}

export default function SettingsForm() {
  const { settings } = useSettings();
  const { pending, engine } = useLive();

  // Known groups keep their order; a plugin that adds a new group still shows
  // up at the end instead of being silently hidden.
  const present = new Set(
    (settings.fields || []).map((field) => field.group).filter(Boolean),
  );
  const groups = [
    ...GROUPS.filter((group) => present.has(group)),
    ...[...present].filter((group) => !GROUPS.includes(group)),
  ];

  return (
    <div className="space-y-5">
      {settings.warnings?.length > 0 && (
        <ul className="space-y-1.5">
          {settings.warnings.map((warning) => (
            <li
              key={warning}
              className="rounded-lg border border-accent/20 bg-accent/[0.08] px-2.5 py-1.5 text-[12px] leading-relaxed text-[#ffcf87]"
            >
              {warning}
            </li>
          ))}
        </ul>
      )}

      {groups.map((group) => {
        const fields = (settings.fields || []).filter(
          (field) =>
            field.group === group &&
            field.key !== "device" &&
            field.key !== "mode" &&
            (!field.mode_only || field.mode_only === settings.values.mode),
        );
        if (!fields.length) return null;
        return (
          <section key={group} className="border-b border-white/5 pb-2 last:border-0">
            <h3 className="mb-2 flex items-center gap-2 text-[12px] font-semibold tracking-[0.09em] text-faint uppercase">
              {GROUP_TITLES[group] || group}
              {group === "engine" && <EngineBadge engine={engine} />}
            </h3>
            {fields.map((field) => (
              <FieldRow key={field.key} field={field} devices={[]} />
            ))}

            {group === "stream" && (
              <div className="mb-2 flex items-center justify-between text-[12px] text-faint">
                <span>Câu đang chờ</span>
                <span className="font-mono text-[12px] text-dim">{pending}</span>
              </div>
            )}
          </section>
        );
      })}

      <PresetPanel />
    </div>
  );
}
