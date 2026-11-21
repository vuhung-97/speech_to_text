// Derived microphone presentation for the Q&A screen: label, level bar and
// warnings. Pure helpers first so the screen itself stays composition-only.

import { SILENT_LEVEL } from "../../shared/mic/constants";
import { levelRatio } from "../../utils/level";

export function isInsecureContext() {
  if (typeof window === "undefined") return false;
  return (
    !window.isSecureContext &&
    !["localhost", "127.0.0.1"].includes(window.location.hostname)
  );
}

export function micLabel({ active, packets, micState, speechBusy, audioPlaying }) {
  if (active) return packets ? "Đang nghe" : "Đang kết nối audio…";
  if (micState === "connecting") return "Đang kết nối mic…";
  if (micState === "error") return "Lỗi mic";
  if (speechBusy || audioPlaying) return "Đang đọc";
  return "Mic tắt";
}

export function useMicStatus({ listen, reader }) {
  const liveText = `${listen.live.stable || ""} ${listen.live.tentative || ""}`.trim();

  return {
    liveText,
    levelPercent: Math.round(levelRatio(listen.level) * 100),
    silentMic:
      listen.active && listen.packets > 0 && listen.level < SILENT_LEVEL,
    insecure: isInsecureContext(),
    micLabel: micLabel({
      active: listen.active,
      packets: listen.packets,
      micState: listen.micState,
      speechBusy: reader.speech.busy,
      audioPlaying: reader.audioPlaying,
    }),
  };
}
