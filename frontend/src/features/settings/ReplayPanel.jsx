import { useCallback, useEffect, useState } from "react";

import { useToast } from "../../shared/ui/ToastProvider";
import { FIELD_CLASS, FIELD_TEXT } from "../../components/ui/fieldStyles";
import * as api from "../../services/api";

export default function ReplayPanel() {
  const { notify } = useToast();
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
        <h3 className="text-[12px] font-semibold tracking-[0.09em] text-faint uppercase">
          Thử nghiệm trên file
        </h3>
        <button
          type="button"
          onClick={refresh}
          className="inline-flex min-h-11 items-center rounded-lg px-2 py-1 text-[12px] text-dim hover:bg-white/5 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:min-h-0"
        >
          Làm mới
        </button>
      </div>

      <div className="flex items-center gap-2">
        <select
          aria-label="Chọn file audio"
          value={selected}
          onChange={(event) => setSelected(event.target.value)}
          className={`${FIELD_CLASS} min-h-11 min-w-0 flex-1 rounded-lg px-2.5 py-2 sm:min-h-0 ${FIELD_TEXT}`}
        >
          {samples.length === 0 && <option value="">— chưa có file —</option>}
          {samples.map((sample) => (
            <option key={sample.name} value={sample.name}>
              {sample.name}
            </option>
          ))}
        </select>
        <label className="flex min-h-11 flex-none cursor-pointer items-center gap-1.5 text-[12px] text-dim sm:min-h-0">
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
        className="mt-2 min-h-11 w-full rounded-lg border border-line bg-white/[0.045] px-3 py-1.5 text-[12.5px] text-white hover:bg-white/[0.085] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-50 sm:min-h-0"
      >
        {busy ? "Đang nhận dạng…" : "Chạy thử"}
      </button>

      {result && (
        <div className="mt-2.5 rounded-xl border border-line bg-white/[0.025] px-3 py-2.5 text-[13px] leading-relaxed">
          <div>{result.text || "— (không có chữ)"}</div>
          <div className="mt-1.5 font-mono text-[12px] tabular-nums text-dim">
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
        className={`mt-2.5 cursor-pointer rounded-xl border border-dashed p-3.5 text-center text-[12px] transition focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-accent ${
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
            className="sr-only"
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
