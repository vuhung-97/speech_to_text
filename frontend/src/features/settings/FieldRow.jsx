import { useEffect, useState } from "react";

import { formatValue } from "../../utils/format";
import { useSettings } from "./SettingsProvider";

export default function FieldRow({ field, devices = [] }) {
  const { settings, dirty, setField } = useSettings();
  const value =
    dirty[field.key] !== undefined ? dirty[field.key] : settings.values[field.key];
  const [draft, setDraft] = useState(value);
  const [text, setText] = useState(value ?? "");

  useEffect(() => setDraft(value), [value]);

  const hint = field.hint ? (
    <p className="mt-1 mb-0 text-[11px] leading-relaxed text-faint">
      {field.hint}
      {field.advanced ? " (nâng cao)" : ""}
    </p>
  ) : null;

  if (field.kind === "enum" || field.kind === "device") {
    const options =
      field.kind === "device"
        ? [
            { value: "", label: "Mặc định (hệ thống)" },
            ...devices.map((device) => ({
              value: String(device.index),
              label: `${device.index} · ${device.name}`,
            })),
          ]
        : field.options.map((option) => ({ value: option, label: option }));
    return (
      <div className="mb-3">
        <label className="mb-1 block text-[13px] text-white">{field.label}</label>
        <select
          value={value}
          onChange={(event) => setField(field, event.target.value)}
          className="w-full rounded-lg border border-line bg-white/[0.04] px-2.5 py-1.5 text-[12.5px] text-white outline-none focus:border-accent/60"
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {hint}
      </div>
    );
  }

  if (field.kind === "bool") {
    return (
      <div className="mb-3">
        <div className="flex items-center justify-between gap-3">
          <span className="text-[13px] text-white">{field.label}</span>
          <button
            type="button"
            role="switch"
            aria-checked={Boolean(value)}
            aria-label={field.label}
            onClick={() => setField(field, !value)}
            className={`relative h-[21px] w-[38px] flex-none rounded-full border transition ${
              value ? "border-accent/50 bg-accent/15" : "border-line bg-white/5"
            }`}
          >
            <span
              className={`absolute top-[2px] left-[2px] h-[15px] w-[15px] rounded-full transition ${
                value ? "translate-x-[17px] bg-accent" : "bg-dim"
              }`}
            />
          </button>
        </div>
        {hint}
      </div>
    );
  }

  if (field.kind === "int" || field.kind === "float") {
    return (
      <div className="mb-3">
        <div className="flex items-center justify-between gap-2">
          <label className="text-[13px] text-white">{field.label}</label>
          <span className="font-mono text-[11px] tabular-nums text-dim">
            {formatValue(field, Number(draft))}
          </span>
        </div>
        <input
          type="range"
          min={field.min}
          max={field.max}
          step={field.step ?? 1}
          value={draft}
          onChange={(event) => setDraft(Number(event.target.value))}
          onPointerUp={() => setField(field, Number(draft))}
          onKeyUp={() => setField(field, Number(draft))}
          onBlur={() => setField(field, Number(draft))}
          className="h-5 w-full"
        />
        {hint}
      </div>
    );
  }

  return (
    <div className="mb-3">
      <label className="mb-1 block text-[13px] text-white">{field.label}</label>
      <textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        onBlur={() => setField(field, text.trim())}
        className="min-h-[58px] w-full resize-y rounded-lg border border-line bg-white/[0.04] px-2.5 py-1.5 text-[12.5px] text-white outline-none focus:border-accent/60"
      />
      {hint}
    </div>
  );
}
