// Q&A screen: conversation on the left, evidence + mic status on the right.

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import AppShell from "../../app/AppShell";
import Badge from "../../components/ui/Badge";
import * as api from "../../services/api";
import { useSpeechPlayer } from "../tts/useSpeechPlayer";
import Composer from "./Composer";
import Thread from "./Thread";
import { useAsk } from "./useAsk";
import { useListen } from "./useListen";

const VOICE_KEY = "tts.voice";
const MIC_KEY = "mic.device";

function PanelSection({ title, children }) {
  return (
    <section className="mb-4 rounded-xl border border-line bg-white/[0.02] p-3">
      <h2 className="m-0 mb-2 text-[11px] font-semibold tracking-[0.08em] text-faint uppercase">
        {title}
      </h2>
      {children}
    </section>
  );
}

export default function QaPage() {
  const { id: routeId } = useParams();
  const [params, setParams] = useSearchParams();
  const [draft, setDraft] = useState("");

  const sessionId = routeId || params.get("session") || "";
  const { turns, busy, error, ask, load } = useAsk(sessionId);
  const [readingId, setReadingId] = useState("");
  const [audioPlaying, setAudioPlaying] = useState(false);
  const [micDevices, setMicDevices] = useState([]);
  const [micDevice, setMicDevice] = useState(
    () => window.localStorage.getItem(MIC_KEY) || "",
  );
  const audioRef = useRef(null);
  const speech = useSpeechPlayer();

  const listen = useListen({
    onText: (heard) =>
      setDraft((previous) =>
        previous.trim()
          ? `${previous.trimEnd()} ${heard}`
          : heard,
      ),
  });

  const refreshMicDevices = useCallback(async () => {
    try {
      const devices = await navigator.mediaDevices?.enumerateDevices?.();
      setMicDevices((devices || []).filter((item) => item.kind === "audioinput"));
    } catch {
      setMicDevices([]);
    }
  }, []);

  useEffect(() => {
    refreshMicDevices();
  }, [refreshMicDevices]);

  const chooseMic = (event) => {
    const value = event.target.value;
    setMicDevice(value);
    window.localStorage.setItem(MIC_KEY, value);
  };

  useEffect(() => {
    if (sessionId) load(sessionId);
  }, [sessionId, load]);

  // New questions keep the URL deep-linkable without remounting the screen.
  useEffect(() => {
    if (routeId || !turns.length) return;
    const active = turns[turns.length - 1];
    const created = active?.answer?.session_id;
    if (created && created !== params.get("session")) {
      const next = new URLSearchParams(params);
      next.set("session", created);
      setParams(next, { replace: true });
    }
  }, [turns, routeId, params, setParams]);

  const handleAsk = useCallback(
    async (question, source) => {
      const data = await ask(question, source);
      if (data) setDraft("");
      return data;
    },
    [ask],
  );

  const submitDraft = useCallback(
    async (question) => {
      let value = question;
      if (listen.active) {
        const heard = await listen.stop(); // closes mic and hands over the text
        if (heard) value = `${value} ${heard}`.trim();
      }
      await handleAsk(value, "typed");
    },
    [handleAsk, listen],
  );

  const read = useCallback(
    async (answer) => {
      if (!answer?.text) return;
      if (listen.active) await listen.stop();
      const voice = window.localStorage.getItem(VOICE_KEY) || "";
      setReadingId(answer.id);
      try {
        const info = await api.getAnswerSpeech(answer.id, voice);
        if (info.mode === "cached" && audioRef.current) {
          speech.stop();
          const element = audioRef.current;
          element.src = info.url;
          element.currentTime = 0;
          await element.play();
          return;
        }
      } catch {
        /* no cache or endpoint unavailable → stream as before */
      }
      speech.start(answer.text, voice);
    },
    [listen, speech],
  );

  const stopReading = useCallback(() => {
    speech.stop();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.removeAttribute("src");
      audioRef.current.load();
    }
    setAudioPlaying(false);
    setReadingId("");
  }, [speech]);

  useEffect(() => {
    if (speech.status === "idle") setReadingId("");
  }, [speech.status]);

  const toggleListen = useCallback(async () => {
    if (listen.active) {
      await listen.stop();
      return;
    }
    stopReading();          // reading and listening are mutually exclusive
    await listen.start(micDevice);
    refreshMicDevices();
  }, [listen, micDevice, refreshMicDevices, stopReading]);

  const lastTurn = turns[turns.length - 1] || null;
  const lastAnswer = lastTurn?.answer || null;
  const liveText = `${listen.live.stable || ""} ${listen.live.tentative || ""}`.trim();
  const liveWords = liveText ? liveText.split(/\s+/).length : 0;
  const insecure =
    typeof window !== "undefined" &&
    !window.isSecureContext &&
    !["localhost", "127.0.0.1"].includes(window.location.hostname);
  const levelPercent = Math.min(
    100,
    Math.round(Math.sqrt(Math.max(0, listen.level)) * 220),
  );
  const silentMic =
    listen.active && listen.packets > 0 && listen.level < 0.002;
  const micLabel = listen.active
    ? listen.packets
      ? "Đang nghe"
      : "Đang kết nối audio…"
    : listen.micState === "connecting"
      ? "Đang kết nối mic…"
      : listen.micState === "error"
        ? "Lỗi mic"
        : speech.busy || audioPlaying
          ? "Đang đọc"
          : "Mic tắt";

  const right = (
    <>
      <PanelSection title="Mic">
        <div className="flex items-center justify-between text-[12px]">
          <span className={listen.active ? "text-accent" : "text-dim"}>
            {micLabel}
          </span>
          <Badge tone={listen.active ? "accent" : "neutral"}>
            {liveWords} từ
          </Badge>
        </div>
        <p className="mt-2 mb-0 line-clamp-4 text-[12px] leading-relaxed text-faint">
          {listen.error
            ? listen.error
            : liveText ||
              (listen.active
                ? listen.packets
                  ? `Đang nghe… (đã gửi ${listen.packets} gói audio)`
                  : "Đang chờ audio từ micro… nếu mãi không đổi, kiểm tra quyền mic."
                : "Mic tắt — bấm Nghe khi muốn nói câu hỏi.")}
        </p>
        {listen.active && (
          <div className="mt-2">
            <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-gradient-to-r from-accent-2 to-accent transition-[width] duration-100"
                style={{ width: `${levelPercent}%` }}
              />
            </div>
            <p className="m-0 mt-1 truncate font-mono text-[10px] text-faint">
              {listen.deviceLabel || "micro mặc định"} · {listen.sampleRate || "?"} Hz
            </p>
          </div>
        )}
        {silentMic && (
          <p className="mt-2 mb-0 rounded-lg border border-accent/30 bg-accent/[0.08] px-2 py-1.5 text-[11px] leading-relaxed text-accent">
            Có gửi audio nhưng mức âm thanh gần 0: chọn micro khác trong danh sách,
            hoặc kiểm tra Windows → Sound → Input.
          </p>
        )}
        {insecure && (
          <p className="mt-2 mb-0 rounded-lg border border-err/35 bg-err/10 px-2 py-1.5 text-[11px] leading-relaxed text-err">
            Trang không chạy HTTPS nên trình duyệt chặn micro. Dùng localhost hoặc
            cấu hình HTTPS cho LAN (xem docs/TRIEN_KHAI_LAN.md).
          </p>
        )}
        {listen.notice && (
          <p className="mt-2 mb-0 rounded-lg border border-accent/30 bg-accent/[0.08] px-2 py-1.5 text-[11px] leading-relaxed text-accent">
            {listen.notice}
          </p>
        )}
        {listen.micState !== "live" && (
          <label className="mt-2 block">
            <span className="sr-only">Thiết bị mic</span>
            <select
              value={micDevice}
              onChange={chooseMic}
              disabled={listen.active}
              className="w-full rounded-lg border border-line bg-white/[0.04] px-2 py-1 text-[11.5px] text-dim outline-none focus:border-accent/60"
            >
              <option value="">Mic mặc định</option>
              {micDevices.map((device, index) => (
                <option key={device.deviceId || index} value={device.deviceId}>
                  {device.label || `Micro ${index + 1}`}
                </option>
              ))}
            </select>
          </label>
        )}
      </PanelSection>

      <PanelSection title="Câu hỏi khớp">
        {lastAnswer?.matched ? (
          <div className="space-y-1.5">
            <p className="m-0 text-[12.5px] leading-relaxed text-white">
              {lastAnswer.matched.question}
            </p>
            <div className="flex items-center gap-1.5">
              <Badge tone="ok">{lastAnswer.matched.percent}%</Badge>
              {lastAnswer.matched.category && (
                <Badge tone="dim">{lastAnswer.matched.category}</Badge>
              )}
            </div>
          </div>
        ) : lastAnswer ? (
          <p className="m-0 text-[12px] leading-relaxed text-faint">
            Câu hỏi chưa có trong kho. Đã ghi vào danh sách “chưa trả lời” để bạn
            bổ sung ở trang Kho câu hỏi.
          </p>
        ) : (
          <p className="m-0 text-[12px] text-faint">
            Chưa có lượt hỏi nào trong phiên này.
          </p>
        )}

        {lastAnswer?.candidates?.length > 0 && (
          <div className="mt-2 space-y-1">
            {lastAnswer.candidates.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => handleAsk(item.question, "typed")}
                className="block w-full truncate rounded-lg px-2 py-1 text-left text-[11.5px] text-dim transition hover:bg-white/[0.06] hover:text-white"
              >
                {item.question} · {item.percent}%
              </button>
            ))}
          </div>
        )}
      </PanelSection>

      <PanelSection title="Đang đọc">
        {speech.busy || audioPlaying ? (
          <div className="space-y-1.5">
            <p className="m-0 text-[12px] text-white">
              {speech.status === "loading" ? "Đang tổng hợp…" : "Đang đọc câu trả lời"}
            </p>
            <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-gradient-to-r from-accent to-accent-2"
                style={{ width: `${Math.round(speech.progress * 100)}%` }}
              />
            </div>
            <p className="m-0 font-mono text-[10.5px] text-faint">
              {speech.seconds.toFixed(1)} s
              {speech.estimated ? ` / ~${Math.round(speech.estimated)} s` : ""}
            </p>
          </div>
        ) : (
          <p className="m-0 text-[12px] text-faint">
            Bấm “Đọc” ở câu trả lời để nghe. Audio được tạo theo luồng, không chờ
            hết văn bản.
          </p>
        )}
      </PanelSection>
    </>
  );

  return (
    <AppShell
      title="Hỏi đáp"
      subtitle={
        sessionId
          ? `Phiên ${sessionId.slice(0, 8)} · ${turns.length} lượt`
          : "Câu hỏi mới"
      }
      right={right}
    >
      <audio
        ref={audioRef}
        className="hidden"
        onPlay={() => setAudioPlaying(true)}
        onPause={() => setAudioPlaying(false)}
        onEnded={() => {
          setAudioPlaying(false);
          setReadingId("");
        }}
      />

      <Thread
        turns={turns}
        onExample={(example) => handleAsk(example, "typed")}
        renderAnswerProps={(turn) => ({
          active: readingId === turn.answer?.id && (speech.busy || audioPlaying),
          playing: readingId === turn.answer?.id && (speech.busy || audioPlaying),
          progress: speech.progress,
          seconds: speech.seconds,
          estimated: speech.estimated,
          downloadUrl:
            readingId === turn.answer?.id ? speech.downloadUrl : "",
          onRead: () => read(turn.answer),
          onStop: stopReading,
          onPick: (question) => handleAsk(question, "typed"),
        })}
      />

      {error && (
        <p className="mx-5 mb-2 rounded-lg border border-err/35 bg-err/10 px-3 py-2 text-[12px] text-err">
          {error}
        </p>
      )}

      <Composer
        value={draft}
        onChange={setDraft}
        onSubmit={submitDraft}
        busy={busy}
        listening={listen.active}
        onToggleListen={toggleListen}
        error={listen.error}
      />
    </AppShell>
  );
}
