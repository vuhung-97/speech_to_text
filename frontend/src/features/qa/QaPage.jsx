// Q&A screen: conversation on the left, evidence + microphone on the right.
// Composition only — listening, reading, devices and conversation state live in
// their own hooks; panels are presentational.

import { useCallback, useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import AppShell from "../../app/AppShell";
import { LEVEL_SCALE, SILENT_LEVEL } from "../mic/constants";
import { useFaqDocuments, DOCUMENT_FILTER_KEY } from "../faq/hooks/useFaqDocuments";
import Composer from "./Composer";
import DocumentPicker from "./DocumentPicker";
import MatchPanel from "./MatchPanel";
import MicPanel from "./MicPanel";
import ReadingPanel from "./ReadingPanel";
import Thread from "./Thread";
import { useAnswerReader } from "./useAnswerReader";
import { useAsk } from "./useAsk";
import { useListen } from "./useListen";
import { useMicDevices } from "./useMicDevices";

export default function QaPage() {
  const { id: routeId } = useParams();
  const [params, setParams] = useSearchParams();
  const [draft, setDraft] = useState("");
  const [documentId, setDocumentId] = useState(
    () => window.localStorage.getItem(DOCUMENT_FILTER_KEY) || "",
  );

  const sessionId = routeId || params.get("session") || "";
  const { turns, busy, error, ask, load } = useAsk(sessionId);
  const documents = useFaqDocuments();
  const listen = useListen({
    onText: (heard) =>
      setDraft((previous) =>
        previous.trim() ? `${previous.trimEnd()} ${heard}` : heard,
      ),
  });
  const reader = useAnswerReader({ onBeforeRead: () => listen.stop() });
  const micDevices = useMicDevices();

  useEffect(() => {
    if (sessionId) load(sessionId);
  }, [sessionId, load]);

  // Keep the chosen set in localStorage and forget it once deleted.
  useEffect(() => {
    window.localStorage.setItem(DOCUMENT_FILTER_KEY, documentId);
  }, [documentId]);

  useEffect(() => {
    if (!documentId) return;
    if (documents.documents.some((document) => document.id === documentId)) return;
    setDocumentId("");
  }, [documentId, documents.documents]);

  // New questions keep the URL deep-linkable without remounting the screen.
  useEffect(() => {
    if (routeId || !turns.length) return;
    const created = turns[turns.length - 1]?.answer?.session_id;
    if (created && created !== params.get("session")) {
      const next = new URLSearchParams(params);
      next.set("session", created);
      setParams(next, { replace: true });
    }
  }, [turns, routeId, params, setParams]);

  const handleAsk = useCallback(
    async (question, source) => {
      const data = await ask(question, source, documentId);
      if (data) setDraft("");
      return data;
    },
    [ask, documentId],
  );

  const submitDraft = useCallback(
    async (question) => {
      let value = question || "";
      if (listen.active) {
        // The finalized sentences are already in the draft; stop() only returns
        // the still-spoken tail so nothing gets submitted twice.
        const tail = await listen.stop();
        if (tail) value = `${value.trimEnd()} ${tail}`.trim();
      }
      if (!value.trim()) return;
      await handleAsk(value, "typed");
    },
    [handleAsk, listen],
  );

  const toggleListen = useCallback(async () => {
    if (listen.active) {
      await listen.stop();
      return;
    }
    reader.stop(); // reading and listening are mutually exclusive
    await listen.start(micDevices.device);
    micDevices.refresh();
  }, [listen, micDevices, reader]);

  const lastAnswer = turns[turns.length - 1]?.answer || null;
  const liveText = `${listen.live.stable || ""} ${listen.live.tentative || ""}`.trim();
  const levelPercent = Math.min(
    100,
    Math.round(Math.sqrt(Math.max(0, listen.level)) * LEVEL_SCALE),
  );
  const silentMic =
    listen.active && listen.packets > 0 && listen.level < SILENT_LEVEL;
  const insecure =
    typeof window !== "undefined" &&
    !window.isSecureContext &&
    !["localhost", "127.0.0.1"].includes(window.location.hostname);
  const micLabel = listen.active
    ? listen.packets
      ? "Đang nghe"
      : "Đang kết nối audio…"
    : listen.micState === "connecting"
      ? "Đang kết nối mic…"
      : listen.micState === "error"
        ? "Lỗi mic"
        : reader.speech.busy || reader.audioPlaying
          ? "Đang đọc"
          : "Mic tắt";

  const right = (
    <>
      <DocumentPicker
        documents={documents.documents}
        value={documentId}
        onChange={setDocumentId}
        disabled={busy}
      />
      <MicPanel
        micLabel={micLabel}
        listen={listen}
        liveText={liveText}
        levelPercent={levelPercent}
        silentMic={silentMic}
        insecure={insecure}
        devices={micDevices.devices}
        device={micDevices.device}
        onChooseMic={micDevices.choose}
      />
      <MatchPanel
        lastAnswer={lastAnswer}
        onPick={(question) => handleAsk(question, "typed")}
      />
      <ReadingPanel speech={reader.speech} audioPlaying={reader.audioPlaying} />
    </>
  );

  return (
    <AppShell
      title="Hỏi đáp"
      subtitle={
        sessionId
          ? `Phiên ${sessionId.slice(0, 8)} · ${turns.length} lượt`
          : "Câu hỏi mới"
      }
      right={right}
    >
      <audio
        ref={reader.audioRef}
        className="hidden"
        onPlay={() => reader.setAudioPlaying(true)}
        onPause={() => reader.setAudioPlaying(false)}
        onEnded={() => {
          reader.setAudioPlaying(false);
          reader.setReadingId("");
        }}
      />

      <Thread
        turns={turns}
        onExample={(example) => handleAsk(example, "typed")}
        renderAnswerProps={(turn) => {
          const isReading = reader.readingId === turn.answer?.id;
          const playing = isReading && (reader.speech.busy || reader.audioPlaying);
          return {
            active: playing,
            playing,
            progress: reader.speech.progress,
            seconds: reader.speech.seconds,
            estimated: reader.speech.estimated,
            downloadUrl: isReading ? reader.speech.downloadUrl : "",
            onRead: () => reader.read(turn.answer),
            onStop: reader.stop,
            onPick: (question) => handleAsk(question, "typed"),
          };
        }}
      />

      {error && (
        <p className="mx-5 mb-2 rounded-lg border border-err/35 bg-err/10 px-3 py-2 text-[12px] text-err">
          {error}
        </p>
      )}

      <Composer
        value={draft}
        live={liveText}
        onChange={setDraft}
        onSubmit={submitDraft}
        busy={busy}
        listening={listen.active}
        onToggleListen={toggleListen}
        error={listen.error}
      />
    </AppShell>
  );
}
