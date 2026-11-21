import { useCallback, useEffect, useRef, useState } from "react";

import * as api from "../../services/api";
import { beginPlayback, endPlayback, isCurrentPlayback } from "../../shared/playback/playbackChannel";
import { useSpeechPlayer } from "../../shared/playback/useSpeechPlayer";
import { readVoice } from "../../shared/tts/constants";

// Reading an answer: cached WAV when available, otherwise the PCM stream.
// One playback channel owns every audible source: starting a read stops
// whatever is playing (stream or cached WAV) synchronously, and late responses
// from an earlier click are discarded via the claim key.
export function useAnswerReader({ onBeforeRead } = {}) {
  const [readingId, setReadingId] = useState("");
  const [audioPlaying, setAudioPlaying] = useState(false);
  const audioRef = useRef(null);
  const speech = useSpeechPlayer();
  const beforeRef = useRef(onBeforeRead);
  const keyRef = useRef(0);

  useEffect(() => {
    beforeRef.current = onBeforeRead;
  }, [onBeforeRead]);

  const silence = useCallback(() => {
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
      if (!isCurrentPlayback(key)) return;

      const voice = readVoice();
      setReadingId(answer.id);

      let info = null;
      try {
        info = await api.getAnswerSpeech(answer.id, voice);
      } catch {
        /* no cache → stream below */
      }
      if (!isCurrentPlayback(key)) return;

      if (info?.mode === "cached" && audioRef.current) {
        const element = audioRef.current;
        element.src = info.url;
        element.currentTime = 0;
        try {
          await element.play();
        } catch {
          // Autoplay rejected: stay silent instead of starting a second
          // source on top of the cached one.
          stop();
        }
        return;
      }

      speech.start(answer.text, voice);
    },
    [speech, silence, stop],
  );

  useEffect(() => {
    if (speech.status === "idle") setReadingId("");
  }, [speech.status]);

  // The element's events are part of this feature, not of the screen.
  const audioProps = {
    onPlay: () => setAudioPlaying(true),
    onPause: () => setAudioPlaying(false),
    onEnded: () => {
      setAudioPlaying(false);
      setReadingId("");
    },
  };

  return {
    speech,
    readingId,
    audioPlaying,
    audioRef,
    audioProps,
    read,
    stop,
  };
}
