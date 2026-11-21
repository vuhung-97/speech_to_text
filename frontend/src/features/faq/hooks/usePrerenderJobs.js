// One background pre-render job per catalogue entry, polled until it settles.

import { useCallback, useEffect, useRef, useState } from "react";

import * as api from "../../../services/api";
import { messageFor } from "../../../services/errors";
import { readVoice } from "../../../shared/tts/constants";

const POLL_MS = 1_500;

export function usePrerenderJobs({ onFinished, onError } = {}) {
  const [jobs, setJobs] = useState({});
  const timers = useRef({});
  const finishedRef = useRef(onFinished);
  const errorRef = useRef(onError);

  useEffect(() => {
    finishedRef.current = onFinished;
    errorRef.current = onError;
  }, [onFinished, onError]);

  useEffect(
    () => () => {
      Object.values(timers.current).forEach((timer) => window.clearInterval(timer));
      timers.current = {};
    },
    [],
  );

  const stopPolling = useCallback((entryId) => {
    if (timers.current[entryId]) {
      window.clearInterval(timers.current[entryId]);
      delete timers.current[entryId];
    }
  }, []);

  const prerender = useCallback(
    async (entry) => {
      const voice = readVoice();
      errorRef.current?.("");
      try {
        const { job } = await api.prerenderFaq(entry.id, voice);
        setJobs((previous) => ({ ...previous, [entry.id]: job }));
        if (job.status === "done") return;

        const poll = window.setInterval(async () => {
          try {
            const status = await api.getPrerender(job.id);
            setJobs((previous) => ({ ...previous, [entry.id]: status }));
            if (status.status !== "running") {
              stopPolling(entry.id);
              finishedRef.current?.();
            }
          } catch {
            stopPolling(entry.id);
          }
        }, POLL_MS);
        timers.current[entry.id] = poll;
      } catch (prerenderError) {
        errorRef.current?.(messageFor(prerenderError));
      }
    },
    [stopPolling],
  );

  return { jobs, prerender };
}
