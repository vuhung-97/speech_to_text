// Q&A screen: conversation on the left, evidence + microphone on the right.
// Composition only — listening, reading, devices and conversation state live in
// their own hooks; panels are presentational.

import { useCallback, useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import AppShell from "../../app/AppShell";
import Alert from "../../components/ui/Alert";
import { useFaqDocuments } from "../faq";
import { useMicStatus } from "./useMicStatus";
import Composer from "./Composer";
import QaSidebar from "./QaSidebar";
import Thread from "./Thread";
import { useAnswerReader } from "./useAnswerReader";
import { useAsk } from "./useAsk";
import { useListen } from "./useListen";
import { useMicDevices } from "./useMicDevices";

export default function QaPage() {
  const { id: routeId } = useParams();
  const [params, setParams] = useSearchParams();
  const [draft, setDraft] = useState("");

  const sessionId = routeId || params.get("session") || "";
  const { turns, busy, loading, error, ask, load } = useAsk(sessionId);
  const documents = useFaqDocuments();
  const documentId = documents.selectedId;
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

  const mic = useMicStatus({ listen, reader });

  return (
    <AppShell
      title="Hỏi đáp"
      right={
        <QaSidebar
          documents={documents.documents}
          documentId={documentId}
          onSelectDocument={documents.select}
          busy={busy}
          mic={mic}
          listen={listen}
          devices={micDevices.devices}
          device={micDevices.device}
          onChooseMic={micDevices.choose}
        />
      }
    >
      {/* Mobile/tablet fallback: the right sidebar is hidden below lg. */}
      <div className="shrink-0 border-b border-line bg-surface/40 p-4 lg:hidden">
        <QaSidebar
          documents={documents.documents}
          documentId={documentId}
          onSelectDocument={documents.select}
          busy={busy}
          mic={mic}
          listen={listen}
          devices={micDevices.devices}
          device={micDevices.device}
          onChooseMic={micDevices.choose}
        />
      </div>

      <Thread
        turns={turns}
        loading={loading}
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

      {error && <Alert className="mx-5 mb-2">{error}</Alert>}

      <Composer
        value={draft}
        live={mic.liveText}
        onChange={setDraft}
        onSubmit={submitDraft}
        busy={busy}
        listening={listen.active}
        onToggleListen={toggleListen}
      />
    </AppShell>
  );
}
