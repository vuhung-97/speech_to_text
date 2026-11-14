// One live recognition stream: browser mic + WebSocket events.
// Used by the Q&A composer and by the dictation page.

import { useCallback, useState } from "react";

import { useMic } from "../mic/useMic";

export function useSpeechStream() {
  const [live, setLive] = useState({ stable: "", tentative: "" });
  const [lastFinal, setLastFinal] = useState({ seq: 0, text: "" });
  const [remoteError, setRemoteError] = useState("");

  const mic = useMic({
    onEvent: (event) => {
      if (event.type === "partial") {
        setLive({
          stable: event.stable || "",
          tentative: event.tentative || "",
        });
      } else if (event.type === "final") {
        setLastFinal((previous) => ({
          seq: previous.seq + 1,
          text: (event.text || "").trim(),
        }));
        setLive({ stable: "", tentative: "" });
      } else if (event.type === "error") {
        setRemoteError(event.detail || "lỗi nhận dạng");
      }
    },
  });

  const clear = useCallback(() => {
    setLive({ stable: "", tentative: "" });
    setRemoteError("");
  }, []);

  return {
    ...mic,
    live,
    lastFinal,
    error: mic.error || remoteError,
    clear,
  };
}

export default useSpeechStream;
