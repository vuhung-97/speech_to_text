// Speech playback state machine: stream → Web Audio, with a real stop.
// No Blob, no full-document buffer: memory is bounded by the player lookahead.
//
// The controller and player are created *before* the first await and registered
// with the playback channel, so a second start (or stop) always cancels the
// right stream even while `player.resume()` is still pending.

import { useCallback, useEffect, useRef, useState } from "react";

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
  const aliveRef = useRef(true);

  const teardown = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    playerRef.current?.stop();
    playerRef.current = null;
    if (keyRef.current) {
      endPlayback(keyRef.current);
      keyRef.current = 0;
    }
  }, []);

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
    async (text, voice) => {
      const controller = new AbortController();
      let sessionId = "";
      let key = 0;
      const player = new PcmPlayer({
        // The claim is released only when the buffer actually finished
        // playing, not when the last byte arrived: the tail must still be
        // stopped by the next owner.
        onDrained: () => {
          if (!isCurrentPlayback(key)) return;
          player.stop();
          if (aliveRef.current) {
            setState({ ...IDLE, status: "done", sessionId });
          }
          endPlayback(key);
        },
      });
      key = beginPlayback(() => {
        controller.abort();
        player.stop();
      });
      // Adopt synchronously so a stop during resume() aborts the right stream.
      playerRef.current = player;
      abortRef.current = controller;
      keyRef.current = key;

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
            player.setSampleRate(sampleRate);
            if (aliveRef.current) {
              setState({
                status: "playing",
                seconds: 0,
                estimated,
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
              setState((previous) => ({ ...previous, seconds }));
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
    [],
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
