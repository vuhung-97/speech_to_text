import { useState } from "react";

import { useSettings } from "../features/settings/SettingsProvider";
import { useToast } from "../app/ToastProvider";
import { loadPresets, savePresets } from "../utils/presets";

export default function PresetPanel() {
  const { settings, dirty, applyPatch } = useSettings();
  const { notify } = useToast();
  const [presets, setPresets] = useState(loadPresets);
  const [name, setName] = useState("");
  const [selected, setSelected] = useState("");
  const names = Object.keys(presets);

  const save = () => {
    const key = name.trim();
    if (!key) {
      notify("Nhập tên preset trước");
      return;
    }
    const snapshot = { ...settings.values, ...dirty };
    delete snapshot.device; // never re-open the microphone from a preset
    const next = { ...presets, [key]: snapshot };
    savePresets(next);
    setPresets(next);
    setName("");
    notify(`Đã lưu preset "${key}"`);
  };

  const load = async () => {
    const snapshot = presets[selected];
    if (!snapshot) {
      notify("Chọn preset trước");
      return;
    }
    const patch = { ...snapshot };
    delete patch.device;
    if (await applyPatch(patch)) notify(`Đã nạp preset "${selected}"`);
  };

  const remove = () => {
    if (!selected) return;
    const next = { ...presets };
    delete next[selected];
    savePresets(next);
    setPresets(next);
    setSelected("");
  };

  return (
    <section>
      <h3 className="mb-2 text-[11px] font-semibold tracking-[0.09em] text-faint uppercase">
        Preset
      </h3>
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="tên preset"
          aria-label="Tên preset"
          className="min-w-0 flex-1 rounded-lg border border-line bg-white/[0.04] px-2.5 py-1.5 text-[12.5px] text-white outline-none placeholder:text-faint focus:border-accent/60"
        />
        <button
          type="button"
          onClick={save}
          className="flex-none rounded-lg border border-line bg-white/[0.045] px-3 py-1.5 text-[12.5px] text-white hover:bg-white/[0.085]"
        >
          Lưu
        </button>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <select
          aria-label="Chọn preset"
          value={selected}
          onChange={(event) => setSelected(event.target.value)}
          className="min-w-0 flex-1 rounded-lg border border-line bg-white/[0.04] px-2.5 py-1.5 text-[12.5px] text-white outline-none focus:border-accent/60"
        >
          <option value="">— chọn —</option>
          {names.map((key) => (
            <option key={key} value={key}>
              {key}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={load}
          className="flex-none rounded-lg border border-line bg-white/[0.045] px-3 py-1.5 text-[12.5px] text-white hover:bg-white/[0.085]"
        >
          Nạp
        </button>
        <button
          type="button"
          onClick={remove}
          className="flex-none rounded-lg px-2 py-1.5 text-[12.5px] text-dim hover:bg-white/5 hover:text-white"
        >
          Xoá
        </button>
      </div>
    </section>
  );
}
