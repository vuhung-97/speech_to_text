import { useCallback, useEffect, useState } from "react";

import { useApp } from "../context/AppContext";
import * as api from "../services/api";

export default function ReplayPanel() {
  const { notify } = useApp();
  const [samples, setSamples] = useState([]);
  const [selected, setSelected] = useState("");
  const [segment, setSegment] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [dragging, setDragging] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const data = await api.getSamples();
      const list = data.samples || [];
      setSamples(list);
      if (list.length) {
        setSelected((current) => current || list[0].name);
      }
    } catch (error) {
      notify(`Không đọc được samples: ${error.message}`);
    }
  }, [notify]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const run = async () => {
    if (!selected) {
      notify("Chưa có file để chạy thử");
      return;
    }
    setBusy(true);
    setResult(null);
    try {
      setResult(await api.replaySample(selected, segment));
    } catch (error) {
      notify(`Lỗi replay: ${error.message}`);
    } finally {
      setBusy(false);
    }
  };

  const upload = async (file) => {
    if (!file) return;
    try {
      const entry = await api.uploadSample(file);
      notify(`Đã thêm ${entry.name}`);
      await refresh();
      setSelected(entry.name);
    } catch (error) {
      notify(`Lỗi upload: ${error.message}`);
    }
  };

  const metrics = result
    ? [
        `audio ${result.audio_s}s`,
        `decode ${result.decode_s}s`,
        `RTF ${result.rtf}`,
        result.truncated ? "cắt 300s" : null,
        result.segments?.length > 1 ? `${result.segments.length} câu` : null,
      ]
        .filter(Boolean)
        .join(" · ")
    : "";

  return (
    <section>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-[11px] font-semibold tracking-[0.09em] text-faint uppercase">
          Thử nghiệm trên file
        </h3>
        <button
          type="button"
          onClick={refresh}
          className="rounded-lg px-2 py-1 text-[11.5px] text-dim hover:bg-white/5 hover:text-white"
        >
          Làm mới
        </button>
      </div>

      <div className="flex items-center gap-2">
        <select
          aria-label="Chọn file audio"
          value={selected}
          onChange={(event) => setSelected(event.target.value)}
          className="min-w-0 flex-1 rounded-lg border border-line bg-white/[0.04] px-2.5 py-1.5 text-[12.5px] text-white outline-none focus:border-accent/60"
        >
          {samples.length === 0 && <option value="">— chưa có file —</option>}
          {samples.map((sample) => (
            <option key={sample.name} value={sample.name}>
              {sample.name}
            </option>
          ))}
        </select>
        <label className="flex flex-none cursor-pointer items-center gap-1.5 text-[11.5px] text-dim">
          <input
            type="checkbox"
            checked={segment}
            onChange={(event) => setSegment(event.target.checked)}
            className="accent-accent"
          />
          chia câu
        </label>
      </div>

      <button
        type="button"
        onClick={run}
        disabled={busy}
        className="mt-2 w-full rounded-lg border border-line bg-white/[0.045] px-3 py-1.5 text-[12.5px] text-white hover:bg-white/[0.085] disabled:opacity-50"
      >
        {busy ? "Đang nhận dạng…" : "Chạy thử"}
      </button>

      {result && (
        <div className="mt-2.5 rounded-xl border border-line bg-white/[0.025] px-3 py-2.5 text-[13px] leading-relaxed">
          <div>{result.text || "— (không có chữ)"}</div>
          <div className="mt-1.5 font-mono text-[10.5px] tabular-nums text-dim">
            {metrics}
          </div>
        </div>
      )}

      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          upload(event.dataTransfer.files?.[0]);
        }}
        className={`mt-2.5 cursor-pointer rounded-xl border border-dashed p-3.5 text-center text-xs transition ${
          dragging
            ? "border-accent bg-accent/10 text-white"
            : "border-white/20 text-faint hover:border-white/35"
        }`}
      >
        <label className="cursor-pointer">
          Kéo file audio vào đây (wav, mp3, m4a…)
          <input
            type="file"
            accept="audio/*,.wav,.mp3,.m4a,.flac,.ogg,.webm"
            className="hidden"
            onChange={(event) => {
              upload(event.target.files?.[0]);
              event.target.value = "";
            }}
          />
        </label>
      </div>
    </section>
  );
}
