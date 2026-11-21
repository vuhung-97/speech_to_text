// Conversation state for the Q&A screen: ask, load a session, keep turns.
// Server state only — the composer's draft lives in the component.

import { useCallback, useEffect, useRef, useState } from "react";

import * as api from "../../services/api";
import { messageFor } from "../../services/errors";

export function useAsk(initialSessionId = "") {
  const [sessionId, setSessionId] = useState(initialSessionId);
  const [title, setTitle] = useState("");
  const [turns, setTurns] = useState([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(Boolean(initialSessionId));
  const [error, setError] = useState("");
  const alive = useRef(true);
  const loadController = useRef(null);
  const askController = useRef(null);
  const inFlight = useRef(false);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      loadController.current?.abort();
      askController.current?.abort();
    };
  }, []);

  const load = useCallback(async (id) => {
    loadController.current?.abort();
    if (!id) {
      setSessionId("");
      setTitle("");
      setTurns([]);
      setError("");
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    loadController.current = controller;
    setLoading(true);
    try {
      const data = await api.getSession(id, { signal: controller.signal });
      if (!alive.current || controller.signal.aborted) return;
      setSessionId(data.id);
      setTitle(data.title || "");
      setTurns(data.turns || []);
      setError("");
    } catch (loadError) {
      if (!alive.current || controller.signal.aborted) return;
      setError(messageFor(loadError));
      setTurns([]);
    } finally {
      if (loadController.current === controller) {
        loadController.current = null;
        if (alive.current) setLoading(false);
      }
    }
  }, []);

  const ask = useCallback(
    async (question, source = "voice", documentId = "") => {
      const value = (question || "").trim();
      if (!value || inFlight.current) return null;

      const controller = new AbortController();
      askController.current = controller;
      inFlight.current = true;
      setBusy(true);
      setError("");
      try {
        const data = await api.askQuestion(value, {
          sessionId: sessionId || null,
          source,
          documentId: documentId || null,
          signal: controller.signal,
        });
        if (!alive.current || controller.signal.aborted) return null;
        setSessionId(data.session_id);
        setTurns((previous) => [
          ...previous,
          {
            id: data.answer.turn_id,
            question: data.question,
            source,
            created_at: Date.now() / 1000,
            answer: data.answer,
          },
        ]);
        return data;
      } catch (askError) {
        if (!controller.signal.aborted && alive.current) {
          setError(messageFor(askError));
        }
        return null;
      } finally {
        inFlight.current = false;
        if (alive.current) setBusy(false);
        if (askController.current === controller) askController.current = null;
      }
    },
    [sessionId],
  );

  return { sessionId, title, turns, busy, loading, error, ask, load, setError };
}
