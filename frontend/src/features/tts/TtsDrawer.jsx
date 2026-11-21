// Reading drawer: voice catalog, text input and the two synthesis modes.
// Data loading lives in useTtsCatalog/useQuickSynth; this file composes them.

import { useEffect, useRef } from "react";
import { useToast } from "../../shared/ui/ToastProvider";
import Alert from "../../components/ui/Alert";
import { useSpeechPlayer } from "../../shared/playback/useSpeechPlayer";
import QuickResult from "./QuickResult";
import StreamProgress from "./StreamProgress";
import TtsTextForm from "./TtsTextForm";
import VoicePicker from "./VoicePicker";
import { useQuickSynth } from "./useQuickSynth";
import { useTtsCatalog } from "./useTtsCatalog";
import { useTtsComposer } from "./useTtsComposer";

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

export default function TtsDrawer({ open, onClose, text: presetText = "" }) {
  const { notify } = useToast();
  const catalog = useTtsCatalog(open);
  const {
    mode,
    setMode,
    text,
    setText,
    words,
    limit,
    charCount,
    overLimit,
    fillFromTranscript,
  } = useTtsComposer(catalog);

  const speech = useSpeechPlayer();
  const { stop: stopSpeech } = speech;
  const quickAudioRef = useRef(null);

  const quick = useQuickSynth({
    onLoaded: () => catalog.setStatus((previous) => ({ ...previous, loaded: true })),
  });
  const { release: releaseQuick } = quick;

  // Closing the drawer must silence the speech immediately.
  useEffect(() => {
    if (!open) {
      stopSpeech();
      quickAudioRef.current?.pause();
      releaseQuick();
    }
  }, [open, stopSpeech, releaseQuick]);

  const switchMode = (next) => {
    setMode(next);
    stopSpeech();
    quickAudioRef.current?.pause();
    releaseQuick();
    quick.setError("");
  };

  const useTranscript = () => fillFromTranscript(presetText, notify);

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
    quickAudioRef.current?.pause();
    releaseQuick();
    await speech.start(value, catalog.voice);
  };

  const startQuick = async () => {
    const value = text.trim();
    if (!value) {
      quick.setError("Nhập văn bản cần đọc trước đã.");
      return;
    }
    stopSpeech();
    await quick.start(value, catalog.voice);
  };

  const needsDownload =
    Object.keys(catalog.status).length > 0 &&
    catalog.available &&
    (catalog.status.local_model === false || catalog.status.offline === false);
  const firstLoad = !catalog.status.loaded;
  const busy = mode === "stream" ? speech.busy : quick.busy;
  const canSubmit = catalog.available && text.trim() && !overLimit && !busy;

  const playerLabel =
    speech.status === "loading"
      ? "Đang tổng hợp…"
      : speech.status === "error"
        ? speech.error
        : speech.status === "done"
          ? "Đã đọc xong"
          : speech.status === "playing"
            ? "Đang đọc"
            : "";

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
          {!catalog.available && (
            <Alert>{catalog.reason || "TTS chưa sẵn sàng."}</Alert>
          )}

          {needsDownload && (
            <Alert tone="accent">
              Chưa đủ model trong <code>models/vieneu</code> — lần đọc đầu sẽ tải từ
              Hugging Face (cần mạng).
            </Alert>
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

          <VoicePicker
            voices={catalog.voices}
            voice={catalog.voice}
            onChange={catalog.chooseVoice}
          />

          <TtsTextForm
            text={text}
            onChange={setText}
            mode={mode}
            words={words}
            charCount={charCount}
            maxWords={catalog.maxWords}
            maxChars={catalog.maxChars}
            overLimit={overLimit}
            onUseTranscript={useTranscript}
            onClear={() => setText("")}
            firstLoad={firstLoad}
            available={catalog.available}
          />

          {mode === "stream" && (
            <StreamProgress speech={speech} label={playerLabel} />
          )}

          {quick.error && <Alert>{quick.error}</Alert>}

          {mode === "quick" && <QuickResult audio={quick.audio} audioRef={quickAudioRef} />}

          {overLimit && (
            <Alert>
              {mode === "stream"
                ? `Vượt ${catalog.maxWords} từ — hãy rút ngắn hoặc chia thành nhiều lần đọc.`
                : `Vượt ${catalog.maxChars} ký tự — chuyển sang "Đọc ngay" để đọc văn bản dài.`}
            </Alert>
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
              : quick.busy
                ? "Đang tạo WAV…"
                : "Tạo WAV"}
          </button>
        </footer>
      </aside>
    </>
  );
}
