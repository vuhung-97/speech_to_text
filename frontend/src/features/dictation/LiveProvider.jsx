// Live dictation state: microphone level, transcript, engine and SSE events.
// One responsibility: everything that changes while the user is speaking.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { useToast } from "../../app/ToastProvider";
import * as api from "../../services/api";
import { connectEvents } from "../../services/sse";
import { countWords, joinTranscript } from "../../utils/format";

const LiveContext = createContext(null);

export const useLive = () => useContext(LiveContext);

const INITIAL_STATUS = {
  state: "connecting",
  paused: false,
  listening: false,
  rtf: null,
  mode: "accurate",
};

export function LiveProvider({ children }) {
  const { notify } = useToast();
  const [status, setStatus] = useState(INITIAL_STATUS);
  const [engine, setEngine] = useState({});
  const [capture, setCapture] = useState({});
  const [pending, setPending] = useState(0);
  const [level, setLevel] = useState(0);
  const [speaking, setSpeaking] = useState(false);
  const [live, setLive] = useState({ stable: "", tentative: "" });
  const [lastFinal, setLastFinal] = useState({ seq: 0, text: "" });
  const [transcript, setTranscript] = useState({ paragraphs: [], openId: null });
  const [snapshot, setSnapshot] = useState({ values: {}, warnings: [] });
  const nextId = useRef(1);

  // ------------------------------------------------------------ transcript
  const appendFinal = useCallback((text, hard) => {
    if (!text) return;
    setTranscript((previous) => {
      const paragraphs = previous.paragraphs.slice();
      if (previous.openId !== null) {
        const index = paragraphs.findIndex((item) => item.id === previous.openId);
        if (index >= 0) {
          paragraphs[index] = {
            ...paragraphs[index],
            text: `${paragraphs[index].text} ${text}`.trim(),
          };
          return { paragraphs, openId: hard ? null : previous.openId };
        }
      }
      const id = nextId.current++;
      paragraphs.push({ id, text });
      return { paragraphs, openId: hard ? null : id };
    });
  }, []);

  // ------------------------------------------------------------------ SSE
  const handleEvent = useCallback(
    (event) => {
      switch (event.type) {
        case "status":
          setStatus({
            state: event.state || "listening",
            paused: Boolean(event.paused),
            listening: event.listening ?? !event.paused,
            rtf: event.rtf ?? null,
            mode: event.mode || "accurate",
          });
          break;
        case "level":
          setLevel(Number(event.value) || 0);
          setSpeaking(Boolean(event.speech));
          break;
        case "partial":
          setLive({ stable: event.stable || "", tentative: event.tentative || "" });
          if (event.rtf != null) setStatus((current) => ({ ...current, rtf: event.rtf }));
          break;
        case "final":
          appendFinal(event.text || "", Boolean(event.hard));
          setLastFinal((previous) => ({
            seq: previous.seq + 1,
            text: (event.text || "").trim(),
          }));
          setLive({ stable: "", tentative: "" });
          break;
        case "queue":
          setPending(Number(event.pending) || 0);
          break;
        case "engine":
          setEngine((previous) => ({ ...previous, ...event }));
          if (event.state === "loading") notify(`Đang nạp ${event.model || "model"}…`);
          else if (event.state === "ready") notify(`Model ${event.model || ""} đã sẵn sàng`);
          else notify(`Nạp model lỗi: ${event.detail || "không rõ"}`);
          break;
        case "warning":
          notify(event.detail || "Cảnh báo");
          break;
        case "error":
          notify(`Lỗi: ${event.detail || "không rõ"}`);
          break;
        case "clear":
          setTranscript({ paragraphs: [], openId: null });
          setLive({ stable: "", tentative: "" });
          break;
        default:
          break;
      }
    },
    [appendFinal, notify],
  );

  useEffect(
    () =>
      connectEvents({
        onEvent: handleEvent,
        onOpen: () =>
          setStatus((current) =>
            current.state === "disconnected" ? { ...current, state: "connecting" } : current,
          ),
        onError: () =>
          setStatus((current) =>
            current.state === "disconnected" ? current : { ...current, state: "disconnected" },
          ),
      }),
    [handleEvent],
  );

  // -------------------------------------------------------------- polling
  useEffect(() => {
    let alive = true;
    let timer = 0;
    const tick = async () => {
      try {
        const data = await api.getState();
        if (!alive) return;
        setEngine(data.engine || {});
        setCapture(data.capture || {});
        setPending(data.queue ?? 0);
        if (data.settings) {
          setSnapshot({
            values: data.settings,
            warnings: data.warnings ?? [],
          });
        }
      } catch {
        /* backend restarting */
      }
      if (alive) timer = window.setTimeout(tick, 2000);
    };
    timer = window.setTimeout(tick, 2000);
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, []);

  // ------------------------------------------------------------ commands
  const togglePause = useCallback(async () => {
    try {
      await api.setPaused(!status.paused);
    } catch (error) {
      notify(`Lỗi: ${error.message}`);
    }
  }, [status.paused, notify]);

  const clearAll = useCallback(async () => {
    try {
      await api.clearTranscript();
    } catch (error) {
      notify(`Lỗi: ${error.message}`);
    }
  }, [notify]);

  const fullText = useMemo(
    () => joinTranscript(transcript.paragraphs, live),
    [transcript, live],
  );
  const words = useMemo(
    () => countWords(transcript.paragraphs, live),
    [transcript, live],
  );

  const value = useMemo(
    () => ({
      status,
      engine,
      capture,
      pending,
      level,
      speaking,
      live,
      lastFinal,
      transcript,
      snapshot,
      fullText,
      words,
      togglePause,
      clearAll,
    }),
    [
      status,
      engine,
      capture,
      pending,
      level,
      speaking,
      live,
      lastFinal,
      transcript,
      snapshot,
      fullText,
      words,
      togglePause,
      clearAll,
    ],
  );

  return <LiveContext.Provider value={value}>{children}</LiveContext.Provider>;
}
