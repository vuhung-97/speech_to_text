// Speech playback state machine: stream → Web Audio, with a real stop.
// No Blob, no full-document buffer: memory is bounded by the player lookahead.

import { useCallback, useEffect, useRef, useState } from "react";

import { messageFor } from "../../services/errors";
import { PcmPlayer } from "./pcmPlayer";
import { streamSpeech, ttsWavUrl } from "./pcmStream";

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
  const aliveRef = useRef(true);

  const teardown = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    playerRef.current?.stop();
    playerRef.current = null;
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
      teardown();
      const player = new PcmPlayer();
      playerRef.current = player;
      try {
        await player.resume(); // inside the click handler → autoplay allowed
      } catch {
        /* resume can fail before a gesture; push() will retry */
      }

      const controller = new AbortController();
      abortRef.current = controller;
      setState({ ...IDLE, status: "loading" });

      try {
        const result = await streamSpeech(text, voice, {
          signal: controller.signal,
          onStart: ({ sampleRate, estimated, sessionId }) => {
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
          onBlock: (block) => player.push(block),
          onProgress: ({ seconds }) => {
            if (aliveRef.current) {
              setState((previous) => ({ ...previous, seconds }));
            }
          },
          onDone: ({ sessionId }) => {
            player.flush();
            if (aliveRef.current) {
              setState((previous) => ({ ...previous, status: "done", sessionId }));
            }
          },
        });
        return result;
      } catch (error) {
        if (!controller.signal.aborted && aliveRef.current) {
          setState({ ...IDLE, status: "error", error: messageFor(error) });
        }
        return null;
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
      }
    },
    [teardown],
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
