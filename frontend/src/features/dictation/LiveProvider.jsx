// Server-side live state: connection status, engine, capture stats, queue and
// settings snapshot. Browser microphone/dictation state lives in the mic
// feature (`useSpeechStream`), not here.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { useToast } from "../../app/ToastProvider";
import * as api from "../../services/api";
import { connectEvents } from "../../services/sse";

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
  const [snapshot, setSnapshot] = useState({ values: {}, warnings: [] });

  const setIfChanged = (setter, value) => {
    setter((previous) =>
      JSON.stringify(previous) === JSON.stringify(value) ? previous : value,
    );
  };

  const syncState = useCallback(async () => {
    try {
      const data = await api.getState();
      setIfChanged(setEngine, data.engine || {});
      setIfChanged(setCapture, data.capture || {});
      setPending((previous) => {
        const next = data.queue ?? 0;
        return previous === next ? previous : next;
      });
      if (data.settings) {
        setIfChanged(setSnapshot, {
          values: data.settings,
          warnings: data.warnings ?? [],
        });
      }
    } catch {
      /* backend restarting; the watchdog retries */
    }
  }, []);

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
        case "queue":
          setPending(Number(event.pending) || 0);
          break;
        case "capture":
          setIfChanged(setCapture, event.capture || {});
          break;
        case "settings":
          setIfChanged(setSnapshot, {
            values: event.values || {},
            warnings: event.warnings || [],
          });
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
        default:
          break;
      }
    },
    [notify],
  );

  useEffect(
    () =>
      connectEvents({
        onEvent: handleEvent,
        onOpen: () => {
          setStatus((current) =>
            current.state === "disconnected" ? { ...current, state: "connecting" } : current,
          );
          syncState();
        },
        onError: () =>
          setStatus((current) =>
            current.state === "disconnected" ? current : { ...current, state: "disconnected" },
          ),
      }),
    [handleEvent, syncState],
  );

  // No periodic polling: state arrives over SSE. One slow sync on mount, when
  // the stream reconnects, and every 60 s while the tab is visible catches a
  // silently dead SSE connection.
  useEffect(() => {
    syncState();
    const tick = () => {
      if (document.visibilityState === "visible") syncState();
    };
    const timer = window.setInterval(tick, 60_000);
    const onVisible = () => {
      if (document.visibilityState === "visible") syncState();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [syncState]);

  const value = useMemo(
    () => ({ status, engine, capture, pending, snapshot }),
    [status, engine, capture, pending, snapshot],
  );

  return <LiveContext.Provider value={value}>{children}</LiveContext.Provider>;
}
