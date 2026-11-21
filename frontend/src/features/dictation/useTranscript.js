// Dictation transcript: append each finalized sentence once, in order.
// Lives outside the screen so the append rule can be tested without rendering.

import { useCallback, useEffect, useRef, useState } from "react";

import { countWords } from "../../utils/format";

const EMPTY = { paragraphs: [], openId: null };

export function useTranscript(lastFinal) {
  const [transcript, setTranscript] = useState(EMPTY);
  const lastSeq = useRef(0);

  useEffect(() => {
    if (lastFinal.seq <= lastSeq.current) return;
    lastSeq.current = lastFinal.seq;
    const text = (lastFinal.text || "").trim();
    if (!text) return;
    setTranscript((previous) => ({
      paragraphs: [
        ...previous.paragraphs,
        { id: previous.paragraphs.length + 1, text },
      ],
      openId: null,
    }));
  }, [lastFinal.seq, lastFinal.text]);

  const clear = useCallback(() => {
    setTranscript({ paragraphs: [], openId: null });
  }, []);

  const fullText = transcript.paragraphs.map((item) => item.text).join(" ").trim();
  return { transcript, clear, fullText, words: countWords(fullText) };
}
