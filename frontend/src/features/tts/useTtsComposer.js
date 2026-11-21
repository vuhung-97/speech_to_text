// Mode, text and limit rules for the reading drawer.
// The drawer keeps playback side effects; this hook owns the composer state so
// the limits are testable without rendering the whole panel.

import { useState } from "react";

import { countWords } from "../../utils/format";

export const TTS_MODES = Object.freeze({ stream: "stream", quick: "quick" });

export function useTtsComposer(catalog) {
  const [mode, setMode] = useState(TTS_MODES.stream);
  const [text, setText] = useState("");

  const words = countWords(text);
  const isStream = mode === TTS_MODES.stream;
  const limit = isStream ? catalog.maxWords : catalog.maxChars;
  const used = isStream ? words : text.length;
  const overLimit = used > limit;

  const fillFromTranscript = (sourceText, notify) => {
    if (!sourceText) {
      notify("Chưa có nội dung nhận dạng để đọc");
      return;
    }
    if (isStream) {
      const parts = sourceText.trim().split(/\s+/);
      if (parts.length > catalog.maxWords) {
        setText(parts.slice(0, catalog.maxWords).join(" "));
        notify(`Transcript dài hơn ${catalog.maxWords} từ — đã cắt bớt`);
      } else {
        setText(sourceText);
      }
      return;
    }
    if (sourceText.length > catalog.maxChars) {
      setText(sourceText.slice(0, catalog.maxChars));
      notify(`Transcript dài hơn ${catalog.maxChars} ký tự — đã cắt bớt`);
    } else {
      setText(sourceText);
    }
  };

  return {
    mode,
    setMode,
    text,
    setText,
    words,
    limit,
    charCount: text.length,
    overLimit,
    fillFromTranscript,
  };
}
