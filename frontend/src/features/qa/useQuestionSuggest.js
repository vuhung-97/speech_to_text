// Watch the live transcript and suggest asking when a sentence reads as a
// question. Server-side detection keeps one source of truth for the rules.

import { useEffect, useRef, useState } from "react";

import * as api from "../../services/api";

const DEBOUNCE_MS = 700;

export function useQuestionSuggest(lastFinalText, { enabled = true } = {}) {
  const [suggestion, setSuggestion] = useState("");
  const asked = useRef("");

  useEffect(() => {
    if (!enabled || !lastFinalText) return undefined;
    if (lastFinalText === asked.current) return undefined;

    const timer = window.setTimeout(async () => {
      try {
        const data = await api.detectQuestion(lastFinalText);
        asked.current = lastFinalText;
        setSuggestion(data.is_question ? data.question : "");
      } catch {
        /* detection is a hint; never block the composer */
      }
    }, DEBOUNCE_MS);

    return () => window.clearTimeout(timer);
  }, [lastFinalText, enabled]);

  return {
    suggestion,
    dismiss: () => setSuggestion(""),
    clear: () => {
      setSuggestion("");
      asked.current = "";
    },
  };
}
