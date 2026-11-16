import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useToast } from "../app/ToastProvider";
import { useSpeechPlayer } from "../features/tts/useSpeechPlayer";
import { VOICE_STORAGE_KEY } from "../features/mic/constants";
import * as api from "../services/api";

const VOICE_KEY = VOICE_STORAGE_KEY;
const FALLBACK_MAX_CHARS = 1000;
const FALLBACK_MAX_WORDS = 2000;

const MODES = [
  { id: "stream", label: "Đọc ngay" },
  { id: "quick", label: "Tạo WAV" },
];

function CloseIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-[18px] w-[18px]"
      aria-hidden="true"
    >
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  );
}

function countWords(value) {
  const text = (value || "").trim();
  return text ? text.split(/\s+/).length : 0;
}

export default function TtsDrawer({ open, onClose, text: presetText = "" }) {
  const { notify } = useToast();
  const sourceText = presetText;
  const [voices, setVoices] = useState([]);
  const [voice, setVoice] = useState("");
  const [defaultVoice, setDefaultVoice] = useState("");
  const [available, setAvailable] = useState(true);
  const [reason, setReason] = useState("");
  const [status, setStatus] = useState({});
  const [maxChars, setMaxChars] = useState(FALLBACK_MAX_CHARS);
  const [maxWords, setMaxWords] = useState(FALLBACK_MAX_WORDS);
  const [mode, setMode] = useState("stream");
  const [text, setText] = useState("");
  const [quickBusy, setQuickBusy] = useState(false);
  const [quickError, setQuickError] = useState("");
  const [quickAudio, setQuickAudio] = useState(null);
  const quickUrlRef = useRef("");
  const urlRef = useRef("");
  const loadedRef = useRef(false);

  const speech = useSpeechPlayer();
  const { stop: stopSpeech } = speech;

  const releaseQuick = useCallback(() => {
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    urlRef.current = "";
    setQuickAudio(null);
  }, []);

  useEffect(
    () => () => {
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
      if (quickUrlRef.current) URL.revokeObjectURL(quickUrlRef.current);
    },
    [],
  );

  // Closing the drawer must silence the speech immediately.
  useEffect(() => {
    if (!open) {
      stopSpeech();
      releaseQuick();
    }
  }, [open, stopSpeech, releaseQuick]);

  const loadVoices = useCallback(async () => {
    try {
      const data = await api.getTtsVoices();
      const list = data.voices || [];
      setVoices(list);
      setDefaultVoice(data.default || "");
      setAvailable(data.available !== false);
      setReason(data.reason || "");
      setStatus(data.status || {});
      setMaxChars(data.max_chars || FALLBACK_MAX_CHARS);
      setMaxWords(data.max_words || FALLBACK_MAX_WORDS);
      setVoice((previous) => {
        if (previous && list.some((item) => item.id === previous)) return previous;
        const saved = window.localStorage.getItem(VOICE_KEY);
        if (saved && list.some((item) => item.id === saved)) return saved;
        return data.default || list[0]?.id || "";
      });
      loadedRef.current = true;
    } catch (loadError) {
      loadedRef.current = false;
      setAvailable(false);
      setReason(`Không tải được danh sách giọng: ${loadError.message}`);
    }
  }, []);

  useEffect(() => {
    if (open && !loadedRef.current) loadVoices();
  }, [open, loadVoices]);

  const chooseVoice = (event) => {
    const value = event.target.value;
    setVoice(value);
    window.localStorage.setItem(VOICE_KEY, value);
  };

  const switchMode = (next) => {
    setMode(next);
    stopSpeech();
    releaseQuick();
    setQuickError("");
  };

  const words = countWords(text);
  const limit = mode === "stream" ? maxWords : maxChars;
  const used = mode === "stream" ? words : text.length;
  const overLimit = used > limit;
  const charCount = text.length;

  const useTranscript = () => {
    if (!sourceText) {
      notify("Chưa có nội dung nhận dạng để đọc");
      return;
    }
    if (mode === "stream") {
      const parts = sourceText.trim().split(/\s+/);
      if (parts.length > maxWords) {
        setText(parts.slice(0, maxWords).join(" "));
        notify(`Transcript dài hơn ${maxWords} từ — đã cắt bớt`);
      } else {
        setText(sourceText);
      }
      return;
    }
    if (sourceText.length > maxChars) {
      setText(sourceText.slice(0, maxChars));
      notify(`Transcript dài hơn ${maxChars} ký tự — đã cắt bớt`);
    } else {
      setText(sourceText);
    }
  };

  const startStream = async () => {
    const value = text.trim();
    if (!value) {
      notify("Nhập văn bản cần đọc trước đã.");
      return;
    }
    if (overLimit) {
      notify(`Văn bản vượt giới hạn ${limit} ${mode === "stream" ? "từ" : "ký tự"}.`);
      return;
    }
    releaseQuick();
    await speech.start(value, voice);
  };

  const startQuick = async () => {
    const value = text.trim();
    if (!value) {
      setQuickError("Nhập văn bản cần đọc trước đã.");
      return;
    }
    setQuickBusy(true);
    setQuickError("");
    try {
      const result = await api.synthesizeSpeech(value, voice);
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
      const url = URL.createObjectURL(result.blob);
      urlRef.current = url;
      setQuickAudio({ url, seconds: result.seconds });
      setStatus((previous) => ({ ...previous, loaded: true }));
    } catch (error) {
      setQuickError(error.message);
    } finally {
      setQuickBusy(false);
    }
  };

  const needsDownload =
    Object.keys(status).length > 0 &&
    available &&
    (status.local_model === false || status.offline === false);
  const firstLoad = !status.loaded;
  const busy = mode === "stream" ? speech.busy : quickBusy;
  const canSubmit = available && text.trim() && !overLimit && !busy;
  const counterTone = overLimit ? "text-err" : "text-faint";

  const playerLabel = useMemo(() => {
    if (speech.status === "loading") return "Đang tổng hợp…";
    if (speech.status === "error") return speech.error;
    if (speech.status === "done") return "Đã đọc xong";
    if (speech.status === "playing") return "Đang đọc";
    return "";
  }, [speech.status, speech.error]);

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
        aria-label="Đọc văn bản"
        aria-hidden={!open}
        inert={open ? undefined : ""}
        className={`fixed top-0 right-0 z-50 flex h-dvh w-[min(460px,100vw)] flex-col border-l border-line bg-gradient-to-b from-surface-2 to-[#0d1014] shadow-[-40px_0_90px_-40px_#000] transition-transform duration-200 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <header className="flex items-start justify-between gap-3 border-b border-line px-5 py-4">
          <div>
            <h2 className="m-0 flex items-center gap-2 text-[15px] font-semibold">
              <span className="grid h-7 w-7 place-items-center rounded-lg bg-accent/15 text-accent">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="h-4 w-4"
                  aria-hidden="true"
                >
                  <path d="M11 5 6 9H3v6h3l5 4V5zM15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13" />
                </svg>
              </span>
              Đọc văn bản
            </h2>
            <p className="mt-1 mb-0 text-[11.5px] text-faint">
              VieNeu v3 Turbo · 48 kHz · phát ngay khi đang tạo
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng"
            className="grid h-8 w-8 place-items-center rounded-lg border border-line bg-white/[0.03] text-dim transition hover:bg-white/[0.075] hover:text-white"
          >
            <CloseIcon />
          </button>
        </header>

        <div className="scroll-thin flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-5">
          {!available && (
            <p className="m-0 rounded-lg border border-err/35 bg-err/10 px-3 py-2 text-[12px] text-err">
              {reason || "TTS chưa sẵn sàng."}
            </p>
          )}

          {needsDownload && (
            <p className="m-0 rounded-lg border border-accent/35 bg-accent/10 px-3 py-2 text-[12px] text-accent">
              Chưa đủ model trong <code>models/vieneu</code> — lần đọc đầu sẽ tải từ
              Hugging Face (cần mạng).
            </p>
          )}

          <div
            role="group"
            aria-label="Chế độ đọc"
            className="grid grid-cols-2 gap-1 rounded-xl border border-line bg-white/[0.03] p-1"
          >
            {MODES.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => switchMode(item.id)}
                aria-pressed={mode === item.id}
                className={`rounded-lg px-3 py-1.5 text-[12.5px] transition ${
                  mode === item.id
                    ? "bg-accent/20 text-accent"
                    : "text-dim hover:bg-white/[0.06] hover:text-white"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>

          <label className="block">
            <span className="mb-1 block text-[13px] text-white">Giọng đọc</span>
            <select
              value={voice}
              onChange={chooseVoice}
              disabled={!voices.length}
              className="w-full rounded-lg border border-line bg-white/[0.04] px-2.5 py-2 text-[13px] text-white outline-none focus:border-accent/60 disabled:opacity-50"
            >
              {!voices.length && <option value="">Chưa có giọng</option>}
              {voices.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>

          <label className="flex min-h-0 flex-1 flex-col">
            <span className="mb-1 flex items-center justify-between text-[13px] text-white">
              <span>Văn bản</span>
              <span className={`font-mono text-[11px] ${counterTone}`}>
                {mode === "stream"
                  ? `${words}/${maxWords} từ · ${charCount} ký tự`
                  : `${charCount}/${maxChars} ký tự`}
              </span>
            </span>
            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="Nhập hoặc dán văn bản cần đọc…"
              className="min-h-[150px] flex-1 resize-none rounded-xl border border-line bg-white/[0.03] px-3 py-2.5 text-[14px] leading-relaxed text-white outline-none placeholder:text-faint focus:border-accent/60"
            />
          </label>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={useTranscript}
              className="rounded-lg border border-line bg-white/[0.04] px-3 py-1.5 text-[12.5px] text-dim transition hover:bg-white/[0.08] hover:text-white"
            >
              Dùng transcript
            </button>
            <button
              type="button"
              onClick={() => setText("")}
              className="rounded-lg px-3 py-1.5 text-[12.5px] text-faint transition hover:bg-white/5 hover:text-white"
            >
              Xoá
            </button>
            {firstLoad && available && (
              <span className="text-[11px] text-faint">
                Lần đầu nạp model ~10–20 giây.
              </span>
            )}
          </div>

          {mode === "stream" && speech.status !== "idle" && (
            <div className="rounded-xl border border-line bg-white/[0.03] p-3">
              <div className="flex items-center justify-between gap-3 text-[12px]">
                <span className={speech.status === "error" ? "text-err" : "text-white"}>
                  {playerLabel}
                </span>
                <span className="font-mono text-[11px] text-faint">
                  {speech.seconds.toFixed(1)} s
                  {speech.estimated ? ` / ~${Math.round(speech.estimated)} s` : ""}
                </span>
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-accent to-accent-2 transition-[width] duration-200"
                  style={{ width: `${Math.round(speech.progress * 100)}%` }}
                />
              </div>
              <div className="mt-2 flex items-center justify-between text-[11.5px]">
                <button
                  type="button"
                  onClick={speech.stop}
                  className="rounded-md px-2 py-1 text-dim transition hover:bg-white/[0.06] hover:text-white"
                >
                  Dừng
                </button>
                {speech.downloadUrl && (
                  <a
                    href={speech.downloadUrl}
                    download
                    className="rounded-md px-2 py-1 text-accent transition hover:bg-accent/10"
                  >
                    Tải WAV
                  </a>
                )}
              </div>
            </div>
          )}

          {quickError && (
            <p className="m-0 rounded-lg border border-err/35 bg-err/10 px-3 py-2 text-[12px] text-err">
              {quickError}
            </p>
          )}

          {mode === "quick" && quickAudio && (
            <div className="rounded-xl border border-line bg-white/[0.03] p-3">
              <audio controls autoPlay src={quickAudio.url} className="w-full" />
              <div className="mt-2 flex items-center justify-between text-[11.5px] text-faint">
                <span>
                  {quickAudio.seconds != null
                    ? `${quickAudio.seconds.toFixed(1)} giây`
                    : "WAV 48 kHz"}
                </span>
                <a
                  href={quickAudio.url}
                  download="vieneu-tts.wav"
                  className="rounded-md px-2 py-1 text-accent transition hover:bg-accent/10"
                >
                  Tải WAV
                </a>
              </div>
            </div>
          )}

          {overLimit && (
            <p className="m-0 rounded-lg border border-err/35 bg-err/10 px-3 py-2 text-[12px] text-err">
              {mode === "stream"
                ? `Vượt ${maxWords} từ — hãy rút ngắn hoặc chia thành nhiều lần đọc.`
                : `Vượt ${maxChars} ký tự — chuyển sang "Đọc ngay" để đọc văn bản dài.`}
            </p>
          )}
        </div>

        <footer className="border-t border-line px-5 py-3">
          <button
            type="button"
            onClick={mode === "stream" ? startStream : startQuick}
            disabled={!canSubmit}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-br from-accent to-accent-2 px-4 py-2.5 text-[13.5px] font-semibold text-[#201505] transition hover:brightness-110 disabled:cursor-default disabled:opacity-45"
          >
            {busy && (
              <span
                className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-[#201505]/35 border-t-[#201505]"
                aria-hidden="true"
              />
            )}
            {mode === "stream"
              ? speech.busy
                ? "Đang đọc…"
                : "Đọc ngay"
              : quickBusy
                ? "Đang tạo WAV…"
                : "Tạo WAV"}
          </button>
        </footer>
      </aside>
    </>
  );
}
