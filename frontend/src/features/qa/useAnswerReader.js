import { useCallback, useEffect, useRef, useState } from "react";

import * as api from "../../services/api";
import { beginPlayback, endPlayback, isCurrentPlayback } from "../../shared/playback/playbackChannel";
import { useSpeechPlayer } from "../../shared/playback/useSpeechPlayer";
import { readSpeed, readVoice } from "../../shared/tts/constants";

// Reading an answer: cached WAV when available, otherwise the PCM stream.
// One playback channel owns every audible source; this hook also owns its
// <audio> element so unmounting the screen always pauses it, even when the ref
// would already be detached.

export const MEDIA_MODE = Object.freeze({
  CACHED: "cached",
  STREAM: "stream",
});

const IDLE_PLAYBACK = { progress: 0, seconds: 0, estimated: 0 };

// One shape for the player UI, whichever source is audible.
function playbackOf(mode, cached, stream) {
  if (mode === MEDIA_MODE.CACHED) return cached;
  if (mode === MEDIA_MODE.STREAM) return stream;
  return IDLE_PLAYBACK;
}

export function useAnswerReader({ onBeforeRead } = {}) {
  const [readingId, setReadingId] = useState("");
  const [readError, setReadError] = useState("");
  const [audioPlaying, setAudioPlaying] = useState(false);
  const [mediaMode, setMediaMode] = useState("");
  const [audioTiming, setAudioTiming] = useState({ seconds: 0, duration: 0 });
  const audioRateRef = useRef(1);
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

    const syncTiming = () => {
      const duration = Number.isFinite(element.duration) ? element.duration : 0;
      const rate = audioRateRef.current || 1;
      setAudioTiming({
        seconds: Math.max(0, (element.currentTime || 0) / rate),
        duration: duration > 0 ? duration / rate : 0,
      });
    };

    const onPlay = () => {
      setAudioPlaying(true);
      syncTiming();
    };
    const onPause = () => setAudioPlaying(false);
    const onEnded = () => {
      setAudioPlaying(false);
      setReadingId("");
      setMediaMode("");
      setAudioTiming({ seconds: 0, duration: 0 });
    };
    element.addEventListener("play", onPlay);
    element.addEventListener("pause", onPause);
    element.addEventListener("ended", onEnded);
    element.addEventListener("loadedmetadata", syncTiming);
    element.addEventListener("durationchange", syncTiming);
    element.addEventListener("timeupdate", syncTiming);
    audioRef.current = element;

    return () => {
      aliveRef.current = false;
      element.removeEventListener("play", onPlay);
      element.removeEventListener("pause", onPause);
      element.removeEventListener("ended", onEnded);
      element.removeEventListener("loadedmetadata", syncTiming);
      element.removeEventListener("durationchange", syncTiming);
      element.removeEventListener("timeupdate", syncTiming);
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
    setReadError("");
    setMediaMode("");
    setAudioTiming({ seconds: 0, duration: 0 });
  }, [speech]);

  const stop = useCallback(() => {
    silence();
    if (keyRef.current) {
      endPlayback(keyRef.current);
      keyRef.current = 0;
    }
  }, [silence]);

  useEffect(() => {
    const onVoiceChange = () => stop();
    window.addEventListener("tts:voice-change", onVoiceChange);
    return () => window.removeEventListener("tts:voice-change", onVoiceChange);
  }, [stop]);

  const read = useCallback(
    async (answer) => {
      if (!answer?.text) return;
      setReadError("");
      // Claiming stops the previous source (stream or cached WAV) right now,
      // before any await, so two reads never overlap.
      const key = beginPlayback(silence);
      keyRef.current = key;
      await beforeRef.current?.();
      if (!aliveRef.current || !isCurrentPlayback(key)) return;

      const voice = readVoice();
      const speed = readSpeed();
      setReadingId(answer.id);
      setMediaMode("");

      let info = null;
      try {
        info = await api.getAnswerSpeech(answer.id, voice);
      } catch {
        /* no cache → stream below */
      }
      if (!aliveRef.current || !isCurrentPlayback(key)) return;

      if (info?.mode === MEDIA_MODE.CACHED && audioRef.current) {
        const element = audioRef.current;
        setMediaMode(MEDIA_MODE.CACHED);
        audioRateRef.current = speed;
        setAudioTiming({ seconds: 0, duration: 0 });
        element.src = info.url;
        element.currentTime = 0;
        // The speed slider is read once per read; changing it must not alter
        // audio that is already playing.
        element.playbackRate = speed;
        element.preservesPitch = true;
        try {
          await element.play();
          // If a newer claim took over while play() was pending, its `silence`
          // already replaced/paused this element — do not touch it here or we
          // would stop the source that replaced us.
        } catch {
          // Autoplay rejected (or superseded): only stop if this claim is
          // still the current one, never the source that replaced it.
          if (isCurrentPlayback(key)) {
            stop();
            setReadError("Không phát được audio. Bấm Đọc để thử lại.");
          }
        }
        return;
      }

      if (!aliveRef.current || !isCurrentPlayback(key)) return;
      // speech.start() claims the playback channel synchronously. That claim
      // stops this reader's own claim (silence), which clears readingId and
      // mediaMode. Re-assert them *after* the handoff, otherwise the audio
      // plays while the card falls back to the plain "Đọc" button.
      speech.start(answer.text, voice, speed);
      setMediaMode(MEDIA_MODE.STREAM);
      setReadingId(answer.id);
    },
    [silence, speech, stop],
  );

  useEffect(() => {
    // `idle` is deliberately not included: cached WAV playback never changes
    // the speech status, and a stream→idle transition during a new cached
    // read must not clear the newly selected answer.
    if (speech.status === "done") setReadingId("");
    if (speech.status === "error") {
      setReadError(speech.error || "Không đọc được câu trả lời.");
      setReadingId("");
    }
  }, [speech.status, speech.error]);

  const audioProgress =
    audioTiming.duration > 0
      ? Math.min(1, audioTiming.seconds / audioTiming.duration)
      : 0;

  // One shape for the player UI, whichever source is audible.
  const playback = playbackOf(
    mediaMode,
    {
      progress: audioProgress,
      seconds: audioTiming.seconds,
      estimated: audioTiming.duration,
    },
    {
      progress: speech.progress,
      seconds: speech.seconds,
      estimated: speech.estimated,
    },
  );

  return {
    speech,
    readingId,
    readError,
    audioPlaying,
    mediaMode,
    playback,
    read,
    stop,
  };
}
