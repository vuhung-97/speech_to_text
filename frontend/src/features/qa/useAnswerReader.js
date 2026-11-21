import { useCallback, useEffect, useRef, useState } from "react";

import * as api from "../../services/api";
import { readVoice } from "../tts/constants";
import { useSpeechPlayer } from "../tts/useSpeechPlayer";

// Reading an answer: cached WAV when available, otherwise the PCM stream.
// The hook owns playback state; the screen only renders it.
export function useAnswerReader({ onBeforeRead } = {}) {
  const [readingId, setReadingId] = useState("");
  const [audioPlaying, setAudioPlaying] = useState(false);
  const audioRef = useRef(null);
  const speech = useSpeechPlayer();
  const beforeRef = useRef(onBeforeRead);

  useEffect(() => {
    beforeRef.current = onBeforeRead;
  }, [onBeforeRead]);

  const stop = useCallback(() => {
    speech.stop();
    const element = audioRef.current;
    if (element) {
      element.pause();
      element.removeAttribute("src");
      element.load();
    }
    setAudioPlaying(false);
    setReadingId("");
  }, [speech]);

  const read = useCallback(
    async (answer) => {
      if (!answer?.text) return;
      await beforeRef.current?.();
      const voice = readVoice();
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
        /* no cache → stream below */
      }
      speech.start(answer.text, voice);
    },
    [speech],
  );

  useEffect(() => {
    if (speech.status === "idle") setReadingId("");
  }, [speech.status]);

  return {
    speech,
    readingId,
    audioPlaying,
    setAudioPlaying,
    setReadingId,
    audioRef,
    read,
    stop,
  };
}
