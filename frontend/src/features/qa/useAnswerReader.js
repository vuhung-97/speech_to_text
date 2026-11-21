import { useCallback, useEffect, useRef, useState } from "react";

import * as api from "../../services/api";
import { beginPlayback, endPlayback, isCurrentPlayback } from "../../shared/playback/playbackChannel";
import { useSpeechPlayer } from "../../shared/playback/useSpeechPlayer";
import { readVoice } from "../../shared/tts/constants";

// Reading an answer: cached WAV when available, otherwise the PCM stream.
// One playback channel owns every audible source; this hook also owns its
// <audio> element so unmounting the screen always pauses it, even when the ref
// would already be detached.
export function useAnswerReader({ onBeforeRead } = {}) {
  const [readingId, setReadingId] = useState("");
  const [audioPlaying, setAudioPlaying] = useState(false);
  const audioRef = useRef(null);
  const speech = useSpeechPlayer();
  const speechStopRef = useRef(speech.stop);
  const beforeRef = useRef(onBeforeRead);
  const keyRef = useRef(0);
  const aliveRef = useRef(true);

  useEffect(() => {
    speechStopRef.current = speech.stop;
  }, [speech.stop]);

  useEffect(() => {
    beforeRef.current = onBeforeRead;
  }, [onBeforeRead]);

  useEffect(() => {
    aliveRef.current = true;
    const element = new Audio();
    element.preload = "auto";
    const onPlay = () => setAudioPlaying(true);
    const onPause = () => setAudioPlaying(false);
    const onEnded = () => {
      setAudioPlaying(false);
      setReadingId("");
    };
    element.addEventListener("play", onPlay);
    element.addEventListener("pause", onPause);
    element.addEventListener("ended", onEnded);
    audioRef.current = element;

    return () => {
      aliveRef.current = false;
      element.removeEventListener("play", onPlay);
      element.removeEventListener("pause", onPause);
      element.removeEventListener("ended", onEnded);
      element.pause();
      element.removeAttribute("src");
      try {
        element.load();
      } catch {
        /* jsdom / older browsers */
      }
      audioRef.current = null;
      speechStopRef.current();
      if (keyRef.current) {
        endPlayback(keyRef.current);
        keyRef.current = 0;
      }
    };
  }, []);

  const silence = useCallback(() => {
    speech.stop();
    const element = audioRef.current;
    if (element) {
      element.pause();
      element.removeAttribute("src");
      try {
        element.load();
      } catch {
        /* jsdom / older browsers */
      }
    }
    setAudioPlaying(false);
    setReadingId("");
  }, [speech]);

  const stop = useCallback(() => {
    silence();
    if (keyRef.current) {
      endPlayback(keyRef.current);
      keyRef.current = 0;
    }
  }, [silence]);

  const read = useCallback(
    async (answer) => {
      if (!answer?.text) return;
      // Claiming stops the previous source (stream or cached WAV) right now,
      // before any await, so two reads never overlap.
      const key = beginPlayback(silence);
      keyRef.current = key;
      await beforeRef.current?.();
      if (!aliveRef.current || !isCurrentPlayback(key)) return;

      const voice = readVoice();
      setReadingId(answer.id);

      let info = null;
      try {
        info = await api.getAnswerSpeech(answer.id, voice);
      } catch {
        /* no cache → stream below */
      }
      if (!aliveRef.current || !isCurrentPlayback(key)) return;

      if (info?.mode === "cached" && audioRef.current) {
        const element = audioRef.current;
        element.src = info.url;
        element.currentTime = 0;
        try {
          await element.play();
          // If a newer claim took over while play() was pending, its `silence`
          // already replaced/paused this element — do not touch it here or we
          // would stop the source that replaced us.
        } catch {
          // Autoplay rejected (or superseded): only stop if this claim is
          // still the current one, never the source that replaced it.
          if (isCurrentPlayback(key)) stop();
        }
        return;
      }

      if (!aliveRef.current || !isCurrentPlayback(key)) return;
      speech.start(answer.text, voice);
    },
    [silence, speech, stop],
  );

  useEffect(() => {
    if (speech.status === "idle") setReadingId("");
  }, [speech.status]);

  return { speech, readingId, audioPlaying, read, stop };
}
