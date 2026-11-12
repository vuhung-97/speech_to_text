import { useCallback, useEffect, useState } from "react";

import { useApp } from "../context/AppContext";
import * as api from "../services/api";
import { formatValue } from "../utils/format";
import PresetPanel from "./PresetPanel";
import ReplayPanel from "./ReplayPanel";

const GROUP_TITLES = {
  mode: "Chế độ",
  engine: "Model & micro",
  vad: "Câu & micro",
  stream: "Luồng (realtime)",
};

const DRAWER_GROUPS = ["mode", "engine", "vad", "stream"];

function EngineBadge({ engine }) {
  if (engine.state === "loading") {
    return (
      <span className="rounded-full border border-accent/40 bg-accent/10 px-2 py-0.5 text-[9.5px] tracking-wide text-accent normal-case">
        đang nạp…
      </span>
    );
  }
  if (engine.state === "error") {
    return (
      <span className="rounded-full border border-err/40 px-2 py-0.5 text-[9.5px] tracking-wide text-err normal-case">
        lỗi nạp
      </span>
    );
  }
  return (
    <span className="rounded-full border border-accent/40 bg-accent/10 px-2 py-0.5 text-[9.5px] tracking-wide text-accent normal-case">
      cần nạp lại khi đổi
    </span>
  );
}

function FieldRow({ field, devices }) {
  const { settings, dirty, setField } = useApp();
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

export default function SettingsDrawer({ open, onClose }) {
  const { settings, dirty, pending, engine, capture, applyDirty, resetSettings } = useApp();
  const [devices, setDevices] = useState([]);

  const loadDevices = useCallback(async () => {
    try {
      const data = await api.getDevices();
      setDevices(data.devices || []);
    } catch {
      setDevices([]);
    }
  }, []);

  useEffect(() => {
    if (open) loadDevices();
  }, [open, loadDevices]);

  const dirtyCount = Object.keys(dirty).length;

  return (
    <>
      <div
        onClick={onClose}
        className={`fixed inset-0 z-40 bg-black/55 backdrop-blur-[2px] transition-opacity ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        aria-hidden="true"
      />

      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Cài đặt"
        aria-hidden={!open}
        className={`fixed top-0 right-0 z-50 flex h-dvh w-[min(430px,100vw)] flex-col border-l border-line bg-gradient-to-b from-surface-2 to-[#0d1014] shadow-[-40px_0_90px_-40px_#000] transition-transform duration-200 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <header className="flex items-center justify-between gap-3 border-b border-line px-5 py-3.5">
          <div>
            <h2 className="m-0 text-[15px] font-semibold">Cài đặt</h2>
            <p className="m-0 mt-0.5 font-mono text-[11px] text-faint">
              {engine.state === "loading"
                ? "đang nạp model…"
                : `${engine.model || "?"} · ${engine.cpu_threads ?? "?"} thread · ${
                    engine.compute_type || "int8"
                  }`}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng cài đặt"
            className="grid h-9 w-9 place-items-center rounded-xl border border-line bg-white/[0.03] text-dim hover:bg-white/[0.075] hover:text-white"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              className="h-4 w-4"
            >
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </header>

        <div className="scroll-thin min-h-0 flex-1 space-y-5 overflow-y-auto px-5 pt-3 pb-6">
          {settings.warnings?.length > 0 && (
            <ul className="space-y-1.5">
              {settings.warnings.map((warning) => (
                <li
                  key={warning}
                  className="rounded-lg border border-accent/20 bg-accent/[0.08] px-2.5 py-1.5 text-[11.5px] leading-relaxed text-[#ffcf87]"
                >
                  {warning}
                </li>
              ))}
            </ul>
          )}

          {DRAWER_GROUPS.map((group) => {
            const fields = settings.fields.filter(
              (field) =>
                field.group === group &&
                (!field.mode_only || field.mode_only === settings.values.mode),
            );
            if (!fields.length) return null;
            return (
              <section key={group} className="border-b border-white/5 pb-2 last:border-0">
                <h3 className="mb-2 flex items-center gap-2 text-[11px] font-semibold tracking-[0.09em] text-faint uppercase">
                  {GROUP_TITLES[group]}
                  {group === "engine" && <EngineBadge engine={engine} />}
                </h3>
                {fields.map((field) => (
                  <FieldRow key={field.key} field={field} devices={devices} />
                ))}

                {group === "engine" && (
                  <div className="mb-2 text-[11.5px] text-faint">
                    <div className="flex items-center justify-between">
                      <span>Thu âm</span>
                      <span className="font-mono text-[11px] text-dim">
                        {capture.backend || "—"} ·{" "}
                        {capture.frames_per_sec != null
                          ? Number(capture.frames_per_sec).toFixed(1)
                          : "—"}{" "}
                        fr/s · {capture.coverage != null
                          ? Math.round(capture.coverage * 100)
                          : "—"}
                        %
                      </span>
                    </div>
                    <p className="mt-1 mb-0 leading-relaxed">
                      dropped {capture.dropped ?? "—"} · xrun {capture.xruns ?? "—"} —
                      nhỏ hơn 9 fr/s hoặc có dropped nghĩa là audio đang bị rơi.
                    </p>
                  </div>
                )}

                {group === "stream" && (
                  <div className="mb-2 flex items-center justify-between text-[11.5px] text-faint">
                    <span>Câu đang chờ</span>
                    <span className="font-mono text-[11px] text-dim">{pending}</span>
                  </div>
                )}
              </section>
            );
          })}

          <ReplayPanel />
          <PresetPanel />
        </div>

        <footer className="flex items-center gap-2.5 border-t border-line px-5 py-3">
          <button
            type="button"
            onClick={applyDirty}
            disabled={dirtyCount === 0}
            className="rounded-xl bg-gradient-to-br from-accent to-accent-2 px-4 py-2 text-[13.5px] font-semibold text-[#201505] transition hover:brightness-110 disabled:cursor-default disabled:opacity-45"
          >
            Áp dụng &amp; nạp lại
          </button>
          <button
            type="button"
            onClick={resetSettings}
            className="rounded-xl px-3 py-2 text-[13.5px] text-dim hover:bg-white/5 hover:text-white"
          >
            Mặc định
          </button>
          <span className="flex-1 text-right text-[11px] text-faint">
            {dirtyCount ? `${dirtyCount} thay đổi cần nạp lại` : "Đổi trực tiếp là áp dụng ngay"}
          </span>
        </footer>
      </aside>
    </>
  );
}
