import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import * as api from "../services/api";
import { connectEvents } from "../services/sse";
import { countWords, joinTranscript } from "../utils/format";

const AppContext = createContext(null);
export const useApp = () => useContext(AppContext);

export function AppProvider({ children }) {
  const [status, setStatus] = useState({
    state: "connecting",
    paused: false,
    rtf: null,
    mode: "accurate",
  });
  const [engine, setEngine] = useState({});
  const [capture, setCapture] = useState({});
  const [pending, setPending] = useState(0);
  const [level, setLevel] = useState(0);
  const [speaking, setSpeaking] = useState(false);
  const [live, setLive] = useState({ stable: "", tentative: "" });
  const [transcript, setTranscript] = useState({ paragraphs: [], openId: null });
  const [settings, setSettings] = useState({
    values: {},
    fields: [],
    engines: [],
    warnings: [],
  });
  const [dirty, setDirty] = useState({});
  const [toast, setToast] = useState({ id: 0, text: "" });
  const nextId = useRef(1);

  const notify = useCallback((text) => {
    if (text) setToast({ id: Date.now(), text });
  }, []);

  // ---------------------------------------------------------------- transcript
  const appendFinal = useCallback((text, hard) => {
    if (!text) return;
    setTranscript((previous) => {
      const paragraphs = previous.paragraphs.slice();
      if (previous.openId !== null) {
        const index = paragraphs.findIndex((p) => p.id === previous.openId);
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

  // ---------------------------------------------------------------- SSE
  const handleEvent = useCallback(
    (event) => {
      switch (event.type) {
        case "status":
          setStatus({
            state: event.state || "listening",
            paused: Boolean(event.paused),
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
          if (event.rtf != null) setStatus((s) => ({ ...s, rtf: event.rtf }));
          break;
        case "final":
          appendFinal(event.text || "", Boolean(event.hard));
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
          setStatus((s) =>
            s.state === "disconnected" ? { ...s, state: "connecting" } : s,
          ),
        onError: () =>
          setStatus((s) =>
            s.state === "disconnected" ? s : { ...s, state: "disconnected" },
          ),
      }),
    [handleEvent],
  );

  // ---------------------------------------------------------------- polling
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
          setSettings((previous) => ({
            ...previous,
            values: data.settings,
            warnings: data.warnings ?? previous.warnings,
          }));
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

  // ---------------------------------------------------------------- settings
  const refreshSettings = useCallback(async () => {
    try {
      setSettings(await api.getSettings());
    } catch (error) {
      notify(`Không tải được cài đặt: ${error.message}`);
    }
  }, [notify]);

  useEffect(() => {
    refreshSettings();
  }, [refreshSettings]);

  const applyPatch = useCallback(
    async (patch) => {
      try {
        const result = await api.postSettings(patch);
        setSettings((previous) => ({
          ...previous,
          values: result.values ?? previous.values,
          fields: result.fields ?? previous.fields,
          engines: result.engines ?? previous.engines,
          warnings: result.warnings ?? previous.warnings,
        }));
        const rejected = result.rejected || {};
        const keys = Object.keys(rejected);
        if (keys.length) {
          notify(`Không hợp lệ: ${keys.map((key) => rejected[key]).join("; ")}`);
          return false;
        }
        return true;
      } catch (error) {
        notify(`Lỗi cài đặt: ${error.message}`);
        return false;
      }
    },
    [notify],
  );

  const setField = useCallback(
    (field, value) => {
      if (field.effect === "live") {
        applyPatch({ [field.key]: value });
      } else {
        setDirty((previous) => ({ ...previous, [field.key]: value }));
      }
    },
    [applyPatch],
  );

  const applyDirty = useCallback(async () => {
    const patch = { ...dirty };
    if (!Object.keys(patch).length) return;
    if (await applyPatch(patch)) {
      setDirty({});
      notify("Đã áp dụng");
    }
  }, [dirty, applyPatch, notify]);

  const resetSettings = useCallback(async () => {
    try {
      const result = await api.resetSettings();
      setSettings((previous) => ({
        ...previous,
        values: result.values ?? previous.values,
        fields: result.fields ?? previous.fields,
        engines: result.engines ?? previous.engines,
        warnings: result.warnings ?? previous.warnings,
      }));
      setDirty({});
      notify("Đã khôi phục mặc định");
    } catch (error) {
      notify(`Lỗi: ${error.message}`);
    }
  }, [notify]);

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

  const fullText = useMemo(() => joinTranscript(transcript.paragraphs, live), [
    transcript,
    live,
  ]);
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
      transcript,
      settings,
      dirty,
      toast,
      fullText,
      words,
      notify,
      setField,
      applyDirty,
      resetSettings,
      refreshSettings,
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
      transcript,
      settings,
      dirty,
      toast,
      fullText,
      words,
      notify,
      setField,
      applyDirty,
      resetSettings,
      refreshSettings,
      togglePause,
      clearAll,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}
