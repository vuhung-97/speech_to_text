// Voice catalog + server-reported limits for the reading drawer.
// Loading never touches the model: the backend only reads JSON assets.

import { useCallback, useEffect, useRef, useState } from "react";

import * as api from "../../services/api";
import {
  FALLBACK_MAX_CHARS,
  FALLBACK_MAX_WORDS,
  readVoice,
  saveVoice,
} from "./constants";

export function useTtsCatalog(open) {
  const [voices, setVoices] = useState([]);
  const [voice, setVoice] = useState("");
  const [available, setAvailable] = useState(true);
  const [reason, setReason] = useState("");
  const [status, setStatus] = useState({});
  const [maxChars, setMaxChars] = useState(FALLBACK_MAX_CHARS);
  const [maxWords, setMaxWords] = useState(FALLBACK_MAX_WORDS);
  const loadedRef = useRef(false);

  const load = useCallback(async () => {
    try {
      const data = await api.getTtsVoices();
      const list = data.voices || [];
      setVoices(list);
      setAvailable(data.available !== false);
      setReason(data.reason || "");
      setStatus(data.status || {});
      setMaxChars(data.max_chars || FALLBACK_MAX_CHARS);
      setMaxWords(data.max_words || FALLBACK_MAX_WORDS);
      setVoice((previous) => {
        if (previous && list.some((item) => item.id === previous)) return previous;
        const saved = readVoice();
        if (saved && list.some((item) => item.id === saved)) return saved;
        return data.default || list[0]?.id || "";
      });
      loadedRef.current = true;
    } catch (error) {
      loadedRef.current = false;
      setAvailable(false);
      setReason(`Không tải được danh sách giọng: ${error.message}`);
    }
  }, []);

  useEffect(() => {
    if (open && !loadedRef.current) load();
  }, [open, load]);

  const chooseVoice = useCallback((value) => {
    setVoice(value);
    saveVoice(value);
  }, []);

  return {
    voices,
    voice,
    available,
    reason,
    status,
    setStatus,
    maxChars,
    maxWords,
    load,
    chooseVoice,
  };
}

export default useTtsCatalog;
