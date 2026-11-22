// One owner for the TTS voice catalog and the selected voice.
// Settings and the reading drawer read the same state, and choosing a voice
// warms that voice in the server RAM in the background.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import * as api from "../../services/api";
import {
  clampSpeed,
  DEFAULT_SPEED,
  readSpeed,
  readVoice,
  saveSpeed,
  saveVoice,
} from "./constants";
import { isPreloadUnsupported } from "./preload";

const VoiceContext = createContext(null);

const PRELOAD_POLL_MS = 800;
const PRELOAD_MAX_ATTEMPTS = 150; // ~2 minutes

const IDLE_WARMUP = { running: false, error: "" };

export const useVoice = () => {
  const value = useContext(VoiceContext);
  if (!value) throw new Error("useVoice must be used inside VoiceProvider");
  return value;
};

const INITIAL = {
  voices: [],
  voice: "",
  speed: DEFAULT_SPEED,
  available: true,
  reason: "",
  status: {},
  loaded: false,
  warmup: IDLE_WARMUP,
};

export function VoiceProvider({ children }) {
  const [state, setState] = useState(() => ({
    ...INITIAL,
    voice: readVoice(),
    speed: readSpeed(),
  }));
  const [loading, setLoading] = useState(true);
  const mounted = useRef(true);
  const pollTimer = useRef(0);
  const pollAttempts = useRef(0);

  const stopPolling = useCallback(() => {
    if (pollTimer.current) {
      window.clearInterval(pollTimer.current);
      pollTimer.current = 0;
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getTtsVoices();
      if (!mounted.current) return;
      const list = data.voices || [];
      const saved = readVoice();
      const voice =
        saved && list.some((item) => item.id === saved)
          ? saved
          : data.default || list[0]?.id || "";
      setState((previous) => ({
        ...previous,
        voices: list,
        voice,
        available: data.available !== false,
        reason: data.reason || "",
        status: data.status || {},
        loaded: true,
        warmup: IDLE_WARMUP,
      }));
    } catch (error) {
      if (!mounted.current) return;
      setState((previous) => ({
        ...previous,
        available: false,
        loaded: false,
        reason: `Không tải được danh sách giọng: ${error.message}`,
      }));
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, []);

  const pollStatus = useCallback(async () => {
    try {
      const status = await api.getTtsStatus();
      if (!mounted.current) return;
      setState((previous) => ({
        ...previous,
        status,
        warmup: {
          running: Boolean(status.preloading),
          error: status.preload_error || "",
        },
      }));
      if (!status.preloading) stopPolling();
      else if (++pollAttempts.current > PRELOAD_MAX_ATTEMPTS) {
        stopPolling();
        setState((previous) => ({
          ...previous,
          warmup: { running: false, error: "Nạp giọng quá lâu — thử lại." },
        }));
      }
    } catch (error) {
      // Older servers do not expose preload/status; the voice still works on
      // the first real read, so this is not a user-facing error.
      if (isPreloadUnsupported(error)) {
        stopPolling();
        setState((previous) => ({ ...previous, warmup: IDLE_WARMUP }));
        return;
      }
      // The status endpoint may be briefly unavailable while the server
      // restarts; keep polling, but stop after the same budget.
      if (++pollAttempts.current > PRELOAD_MAX_ATTEMPTS) {
        stopPolling();
        setState((previous) => ({
          ...previous,
          warmup: {
            running: false,
            error: "Không đọc được trạng thái nạp giọng.",
          },
        }));
      }
    }
  }, [stopPolling]);

  const preload = useCallback(
    async (voice) => {
      if (!voice) return;
      stopPolling();
      pollAttempts.current = 0;
      setState((previous) => ({
        ...previous,
        warmup: { running: true, error: "" },
      }));
      try {
        await api.preloadTts(voice);
      } catch (error) {
        if (!mounted.current) return;
        setState((previous) => ({
          ...previous,
          warmup: {
            running: false,
            error: isPreloadUnsupported(error) ? "" : error.message,
          },
        }));
        return;
      }
      if (!mounted.current) return;
      pollStatus();
      pollTimer.current = window.setInterval(pollStatus, PRELOAD_POLL_MS);
    },
    [pollStatus, stopPolling],
  );

  const chooseVoice = useCallback(
    (value) => {
      setState((previous) => ({ ...previous, voice: value }));
      saveVoice(value);
      // The answer reader subscribes so a voice change never leaves old audio
      // playing under the new selection.
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("tts:voice-change"));
      }
      preload(value);
    },
    [preload],
  );

  const chooseSpeed = useCallback((value) => {
    const speed = clampSpeed(value);
    setState((previous) => ({ ...previous, speed }));
    saveSpeed(speed);
  }, []);

  useEffect(() => {
    mounted.current = true;
    load();
    return () => {
      mounted.current = false;
      stopPolling();
    };
  }, [load, stopPolling]);

  const value = useMemo(
    () => ({
      ...state,
      loading,
      preloading: state.warmup.running,
      preloadError: state.warmup.error,
      load,
      preload,
      chooseVoice,
      chooseSpeed,
    }),
    [state, loading, load, preload, chooseVoice, chooseSpeed],
  );

  return (
    <VoiceContext.Provider value={value}>{children}</VoiceContext.Provider>
  );
}

export default VoiceProvider;
