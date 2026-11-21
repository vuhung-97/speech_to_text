// Quick mode: one POST that returns a finished WAV blob.
// Object URLs are revoked here so the drawer never leaks memory.

import { useCallback, useEffect, useRef, useState } from "react";

import * as api from "../../services/api";

export function useQuickSynth({ onLoaded } = {}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [audio, setAudio] = useState(null);
  const urlRef = useRef("");
  const onLoadedRef = useRef(onLoaded);

  useEffect(() => {
    onLoadedRef.current = onLoaded;
  }, [onLoaded]);

  const release = useCallback(() => {
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    urlRef.current = "";
    setAudio(null);
  }, []);

  useEffect(
    () => () => {
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    },
    [],
  );

  const start = useCallback(async (text, voice) => {
    setBusy(true);
    setError("");
    try {
      const result = await api.synthesizeSpeech(text, voice);
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
      const url = URL.createObjectURL(result.blob);
      urlRef.current = url;
      setAudio({ url, seconds: result.seconds });
      onLoadedRef.current?.();
      return true;
    } catch (synthError) {
      setError(synthError.message);
      return false;
    } finally {
      setBusy(false);
    }
  }, []);

  return { busy, error, audio, start, release, setError };
}

export default useQuickSynth;
