// Speech playback state machine: stream → Web Audio, with a real stop.
// No Blob, no full-document buffer: memory is bounded by the player lookahead.
//
// The controller and player are created *before* the first await and registered
// with the playback channel, so a second start (or stop) always cancels the
// right stream even while `player.resume()` is still pending.

import { useCallback, useEffect, useRef, useState } from "react";

import { cancelTtsSession } from "../../services/api";
import { messageFor } from "../../services/errors";
import { PcmPlayer } from "./pcmPlayer";
import { streamSpeech, ttsWavUrl } from "./pcmStream";
import { beginPlayback, endPlayback, isCurrentPlayback } from "./playbackChannel";

const IDLE = {
  status: "idle", // idle | loading | playing | done | error
  seconds: 0,
  estimated: 0,
  sessionId: "",
  error: "",
};

export function useSpeechPlayer() {
  const [state, setState] = useState(IDLE);
  const playerRef = useRef(null);
  const abortRef = useRef(null);
  const keyRef = useRef(0);
  const sessionRef = useRef("");
  const aliveRef = useRef(true);

  const cancelSession = useCallback((sessionId) => {
    if (!sessionId) return;
    cancelTtsSession(sessionId).catch(() => {
      /* the job may already be finished/removed */
    });
  }, []);

  const teardown = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    playerRef.current?.stop();
    playerRef.current = null;
    // Aborting the HTTP body is not enough: the server may still be busy for
    // a few seconds. Delete the job so a new read can start immediately.
    cancelSession(sessionRef.current);
    sessionRef.current = "";
    if (keyRef.current) {
      endPlayback(keyRef.current);
      keyRef.current = 0;
    }
  }, [cancelSession]);

  useEffect(() => {
    aliveRef.current = true;
    return () => {
      aliveRef.current = false;
      teardown();
    };
  }, [teardown]);

  const stop = useCallback(() => {
    teardown();
    setState((previous) =>
      previous.status === "idle" ? previous : { ...previous, status: "idle" },
    );
  }, [teardown]);

  const start = useCallback(
    async (text, voice, speed = 1) => {
      const rate = Math.min(3, Math.max(0.5, Number(speed) || 1));
      const controller = new AbortController();
      let sessionId = "";
      let key = 0;
      const player = new PcmPlayer({
        speed: rate,
        // The claim is released only when the buffer actually finished
        // playing, not when the last byte arrived: the tail must still be
        // stopped by the next owner.
        onDrained: () => {
          if (!isCurrentPlayback(key)) return;
          player.stop();
          // The WAV is finished and still downloadable; do not delete it.
          sessionRef.current = "";
          if (aliveRef.current) {
            setState({ ...IDLE, status: "done", sessionId });
          }
          endPlayback(key);
        },
      });
      key = beginPlayback(() => {
        controller.abort();
        player.stop();
        cancelSession(sessionId);
        if (aliveRef.current) {
          setState((previous) =>
            previous.status === "idle" ? previous : { ...previous, status: "idle" },
          );
        }
      });
      // Adopt synchronously so a stop during resume() aborts the right stream.
      playerRef.current = player;
      abortRef.current = controller;
      keyRef.current = key;
      sessionRef.current = "";

      try {
        await player.resume(); // inside the click handler → autoplay allowed
      } catch {
        /* resume can fail before a gesture; push() schedules once it can */
      }
      if (!aliveRef.current || !isCurrentPlayback(key)) {
        controller.abort();
        player.stop();
        endPlayback(key);
        return null;
      }

      setState({ ...IDLE, status: "loading" });

      try {
        const result = await streamSpeech(text, voice, {
          signal: controller.signal,
          onStart: ({ sampleRate, estimated, sessionId: started }) => {
            if (!isCurrentPlayback(key)) return;
            sessionId = started;
            sessionRef.current = started;
            player.setSampleRate(sampleRate);
            if (aliveRef.current) {
              setState({
                status: "playing",
                seconds: 0,
                // Header duration is audio time; show wall-clock time at the
                // chosen playback rate (2x → half the seconds).
                estimated: estimated / rate,
                sessionId,
                error: "",
              });
            }
          },
          onBlock: (block) => {
            if (!isCurrentPlayback(key)) return undefined;
            // Awaiting this promise is the HTTP backpressure signal.
            return player.push(block);
          },
          onProgress: ({ seconds }) => {
            if (isCurrentPlayback(key) && aliveRef.current) {
              setState((previous) => ({ ...previous, seconds: seconds / rate }));
            }
          },
          onDone: ({ sessionId: finished }) => {
            if (finished) sessionId = finished;
            player.flush(); // "done" is set when the buffer actually drains
          },
        });
        return result;
      } catch (error) {
        player.stop();
        if (!controller.signal.aborted && isCurrentPlayback(key) && aliveRef.current) {
          setState({ ...IDLE, status: "error", error: messageFor(error) });
        }
        endPlayback(key);
        return null;
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
      }
    },
    [cancelSession],
  );

  const progress =
    state.estimated > 0 ? Math.min(1, state.seconds / state.estimated) : 0;
  const downloadUrl =
    state.sessionId && (state.status === "done" || state.status === "playing")
      ? ttsWavUrl(state.sessionId)
      : "";

  return {
    ...state,
    progress,
    downloadUrl,
    busy: state.status === "loading" || state.status === "playing",
    start,
    stop,
  };
}
