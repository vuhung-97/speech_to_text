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
  const [error, setError] = useState("");
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  const load = useCallback(async (id) => {
    if (!id) {
      setSessionId("");
      setTitle("");
      setTurns([]);
      setError("");
      return;
    }
    try {
      const data = await api.getSession(id);
      if (!alive.current) return;
      setSessionId(data.id);
      setTitle(data.title || "");
      setTurns(data.turns || []);
      setError("");
    } catch (loadError) {
      if (!alive.current) return;
      setError(messageFor(loadError));
      setTurns([]);
    }
  }, []);

  const ask = useCallback(
    async (question, source = "voice") => {
      const value = (question || "").trim();
      if (!value) return null;
      setBusy(true);
      setError("");
      try {
        const data = await api.askQuestion(value, {
          sessionId: sessionId || null,
          source,
        });
        if (!alive.current) return null;
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
        if (alive.current) setError(messageFor(askError));
        return null;
      } finally {
        if (alive.current) setBusy(false);
      }
    },
    [sessionId],
  );

  return { sessionId, title, turns, busy, error, ask, load, setError };
}
