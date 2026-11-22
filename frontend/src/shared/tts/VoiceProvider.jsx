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
import { readVoice, saveVoice } from "./constants";

const VoiceContext = createContext(null);

const PRELOAD_POLL_MS = 800;
const PRELOAD_MAX_ATTEMPTS = 150; // ~2 minutes

export const useVoice = () => {
  const value = useContext(VoiceContext);
  if (!value) throw new Error("useVoice must be used inside VoiceProvider");
  return value;
};

const INITIAL = {
  voices: [],
  voice: "",
  available: true,
  reason: "",
  status: {},
  loaded: false,
  preloading: false,
  preloadError: "",
};

export function VoiceProvider({ children }) {
  const [state, setState] = useState(() => ({
    ...INITIAL,
    voice: readVoice(),
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
        preloadError: "",
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
        preloading: Boolean(status.preloading),
        preloadError: status.preload_error || "",
      }));
      if (!status.preloading) stopPolling();
      else if (++pollAttempts.current > PRELOAD_MAX_ATTEMPTS) {
        stopPolling();
        setState((previous) => ({
          ...previous,
          preloading: false,
          preloadError: "Nạp giọng quá lâu — thử lại.",
        }));
      }
    } catch {
      // keep polling; the status endpoint may be briefly unavailable
    }
  }, [stopPolling]);

  const preload = useCallback(
    async (voice) => {
      if (!voice) return;
      stopPolling();
      pollAttempts.current = 0;
      setState((previous) => ({
        ...previous,
        preloading: true,
        preloadError: "",
      }));
      try {
        await api.preloadTts(voice);
      } catch (error) {
        if (!mounted.current) return;
        setState((previous) => ({
          ...previous,
          preloading: false,
          preloadError: error.message,
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
      preload(value);
    },
    [preload],
  );

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
      load,
      preload,
      chooseVoice,
    }),
    [state, loading, load, preload, chooseVoice],
  );

  return (
    <VoiceContext.Provider value={value}>{children}</VoiceContext.Provider>
  );
}

export default VoiceProvider;
