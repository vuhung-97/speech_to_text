import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import LevelMeter from "../components/LevelMeter";
import Alert from "../components/ui/Alert";
import ControlsBar from "../components/ControlsBar";
import SettingsDrawer from "../features/settings/SettingsDrawer";
import StatusPill from "../components/StatusPill";
import TranscriptView from "../components/TranscriptView";
import TtsDrawer from "../features/tts/TtsDrawer";
import { useLive } from "../features/dictation/LiveProvider";
import { useSpeechStream } from "../features/mic/useSpeechStream";
import { useToast } from "../app/ToastProvider";
import { readMicDevice } from "../features/mic/constants";
import { countWords } from "../utils/format";

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <span className="grid h-[38px] w-[38px] place-items-center rounded-xl bg-gradient-to-br from-accent to-accent-2 text-[#1a1206] shadow-[0_10px_24px_-12px_rgba(255,138,61,0.9)]">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-[19px] w-[19px]"
        >
          <rect x="9" y="2" width="6" height="12" rx="3" />
          <path d="M5 10v1a7 7 0 0 0 14 0v-1M12 18v4" />
        </svg>
      </span>
      <div>
        <h1 className="m-0 text-base font-semibold tracking-tight">Đọc chính tả</h1>
        <p className="m-0 mt-px text-[11.5px] tracking-[0.04em] text-faint uppercase max-sm:hidden">
          mic trình duyệt · offline · realtime
        </p>
      </div>
    </div>
  );
}

export default function DictationPage() {
  const { engine, status: serverStatus } = useLive();
  const { notify } = useToast();
  const stream = useSpeechStream();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [ttsOpen, setTtsOpen] = useState(false);
  const [transcript, setTranscript] = useState({ paragraphs: [], openId: null });
  const lastSeq = useRef(0);

  const listening = stream.state === "live";
  const connecting = stream.state === "connecting";

  useEffect(() => {
    if (stream.lastFinal.seq <= lastSeq.current) return;
    lastSeq.current = stream.lastFinal.seq;
    const text = stream.lastFinal.text;
    if (!text) return;
    setTranscript((previous) => ({
      paragraphs: [
        ...previous.paragraphs,
        { id: previous.paragraphs.length + 1, text },
      ],
      openId: null,
    }));
  }, [stream.lastFinal.seq, stream.lastFinal.text]);

  const toggle = useCallback(async () => {
    if (listening || connecting) {
      await stream.stop();
      return;
    }
    await stream.start(readMicDevice());
  }, [connecting, listening, stream]);

  const clearAll = () => {
    setTranscript({ paragraphs: [], openId: null });
    stream.clear();
  };

  const fullText = transcript.paragraphs.map((item) => item.text).join(" ").trim();
  const words = countWords(fullText);
  const live = stream.live;

  const copy = async () => {
    if (!fullText) {
      notify("Chưa có nội dung để sao chép");
      return;
    }
    try {
      await navigator.clipboard.writeText(fullText);
      notify("Đã sao chép");
    } catch {
      notify("Trình duyệt không cho phép sao chép");
    }
  };

  useEffect(() => {
    const onKeyDown = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === ",") {
        event.preventDefault();
        setDrawerOpen((open) => !open);
        return;
      }
      if (event.key !== "Escape" || event.ctrlKey || event.altKey || event.metaKey) {
        return;
      }
      event.preventDefault();
      if (ttsOpen) setTtsOpen(false);
      else if (drawerOpen) setDrawerOpen(false);
      else toggle();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [drawerOpen, ttsOpen, toggle]);

  const pillState = listening ? "listening" : connecting ? "starting" : "paused";
  const pillLabel = listening ? "Đang nghe" : connecting ? "Đang kết nối…" : "Mic tắt";

  return (
    <div className={listening ? "" : "paused"}>
      <div
        className="pointer-events-none fixed inset-x-0 -top-[30%] h-[60vh] bg-[radial-gradient(60%_100%_at_50%_100%,rgba(255,180,84,0.10),transparent_70%)]"
        aria-hidden="true"
      />
      <div className="relative mx-auto flex h-dvh max-w-[940px] flex-col gap-4 px-6 pt-6 pb-4 max-sm:px-3.5 max-sm:pt-4">
        <header className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link
              to="/"
              aria-label="Về trang hỏi đáp"
              title="Về trang hỏi đáp"
              className="grid h-9 w-9 place-items-center rounded-xl border border-line bg-white/[0.03] text-dim transition hover:bg-white/[0.075] hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
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
                <path d="M19 12H5M12 19l-7-7 7-7" />
              </svg>
            </Link>
            <Brand />
          </div>
          <div className="flex items-center gap-2.5">
            <StatusPill state={pillState} label={pillLabel} />
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              aria-label="Cài đặt"
              title="Cài đặt (Ctrl+Comma)"
              className="grid h-9 w-9 place-items-center rounded-xl border border-line bg-white/[0.03] text-dim transition hover:bg-white/[0.075] hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
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
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </button>
          </div>
        </header>

        {stream.error && <Alert>{stream.error}</Alert>}

        <LevelMeter level={stream.level} speaking={listening && Boolean(live.stable || live.tentative)} />

        <main className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[20px] border border-line bg-surface shadow-[0_40px_90px_-50px_#000]">
          <TranscriptView
            transcript={transcript}
            live={live}
            speaking={listening}
            paused={!listening}
          />
          <ControlsBar
            listening={listening}
            onToggle={toggle}
            engine={engine}
            pending={0}
            words={words}
            fullText={fullText}
            onOpenTts={() => setTtsOpen(true)}
            onClear={clearAll}
            onCopy={copy}
            mode={serverStatus?.mode || "accurate"}
            rtf={serverStatus?.rtf ?? null}
          />
        </main>

        <p className="m-0 hidden text-center text-[12px] text-faint sm:block">
          Mic chạy trong trình duyệt · nghỉ ~0.6 giây để chốt câu ·{" "}
          <kbd className="rounded border border-line bg-white/[0.04] px-1.5 py-px font-mono text-[10.5px] text-dim">
            Esc
          </kbd>{" "}
          bật / tắt mic ·{" "}
          <kbd className="rounded border border-line bg-white/[0.04] px-1.5 py-px font-mono text-[10.5px] text-dim">
            Ctrl
          </kbd>
          +
          <kbd className="rounded border border-line bg-white/[0.04] px-1.5 py-px font-mono text-[10.5px] text-dim">
            ,
          </kbd>{" "}
          cài đặt
        </p>
      </div>

      <SettingsDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
      <TtsDrawer open={ttsOpen} onClose={() => setTtsOpen(false)} text={fullText} />
    </div>
  );
}
