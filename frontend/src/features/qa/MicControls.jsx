// Compact microphone card used in the Q&A sidebar: state, level and device.

import { FIELD_CLASS, FIELD_TEXT } from "../../components/ui/fieldStyles";

export default function MicControls({
  label,
  listen,
  levelPercent,
  devices = [],
  device = "",
  onChooseMic,
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <span
          className={`min-w-0 truncate text-[12px] ${
            listen.active ? "text-accent" : "text-faint"
          }`}
        >
          {label}
        </span>
        {listen.active && (
          <span className="h-1.5 w-20 shrink-0 overflow-hidden rounded-full bg-white/10">
            <span
              className="block h-full rounded-full bg-gradient-to-r from-accent-2 to-accent"
              style={{ width: `${levelPercent}%` }}
            />
          </span>
        )}
      </div>

      <select
        aria-label="Thiết bị mic"
        value={device}
        onChange={(event) => onChooseMic?.(event.target.value)}
        disabled={listen.active}
        className={`${FIELD_CLASS} min-h-11 w-full rounded-lg px-2 py-1.5 sm:min-h-0 ${FIELD_TEXT}`}
      >
        <option value="">Mic mặc định</option>
        {devices.map((item, index) => (
          <option key={item.deviceId || index} value={item.deviceId}>
            {item.label || `Micro ${index + 1}`}
          </option>
        ))}
      </select>
    </div>
  );
}
