// Q&A screen: conversation on the left, evidence + mic status on the right.

import { useCallback, useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import AppShell from "../../app/AppShell";
import Badge from "../../components/ui/Badge";
import { useApp } from "../../context/AppContext";
import { useSpeechPlayer } from "../tts/useSpeechPlayer";
import Composer from "./Composer";
import Thread from "./Thread";
import { useAsk } from "./useAsk";
import { useQuestionSuggest } from "./useQuestionSuggest";

const VOICE_KEY = "tts.voice";

function PanelSection({ title, children }) {
  return (
    <section className="mb-4 rounded-xl border border-line bg-white/[0.02] p-3">
      <h2 className="m-0 mb-2 text-[11px] font-semibold tracking-[0.08em] text-faint uppercase">
        {title}
      </h2>
      {children}
    </section>
  );
}

export default function QaPage() {
  const { id: routeId } = useParams();
  const [params, setParams] = useSearchParams();
  const { transcript, live, fullText, words, speaking } = useApp();

  const sessionId = routeId || params.get("session") || "";
  const { turns, busy, error, ask, load } = useAsk(sessionId);
  const [readingId, setReadingId] = useState("");
  const speech = useSpeechPlayer();

  const lastFinal = transcript.paragraphs.at(-1)?.text || "";
  const { suggestion, dismiss, clear } = useQuestionSuggest(lastFinal);

  useEffect(() => {
    if (sessionId) load(sessionId);
  }, [sessionId, load]);

  // New questions keep the URL deep-linkable without remounting the screen.
  useEffect(() => {
    if (routeId || !turns.length) return;
    const active = turns[turns.length - 1];
    const created = active?.answer?.session_id;
    if (created && created !== params.get("session")) {
      const next = new URLSearchParams(params);
      next.set("session", created);
      setParams(next, { replace: true });
    }
  }, [turns, routeId, params, setParams]);

  const handleAsk = useCallback(
    async (question, source) => {
      const data = await ask(question, source);
      if (data) clear();
      return data;
    },
    [ask, clear],
  );

  const read = useCallback(
    (answer) => {
      if (!answer?.text) return;
      setReadingId(answer.id);
      const voice = window.localStorage.getItem(VOICE_KEY) || "";
      speech.start(answer.text, voice);
    },
    [speech],
  );

  const stopReading = useCallback(() => {
    speech.stop();
    setReadingId("");
  }, [speech]);

  useEffect(() => {
    if (speech.status === "idle") setReadingId("");
  }, [speech.status]);

  const lastTurn = turns[turns.length - 1] || null;
  const lastAnswer = lastTurn?.answer || null;
  const liveText = `${live.stable || ""} ${live.tentative || ""}`.trim();

  const right = (
    <>
      <PanelSection title="Mic">
        <div className="flex items-center justify-between text-[12px]">
          <span className={speaking ? "text-accent" : "text-dim"}>
            {speaking ? "Đang nghe bạn nói" : "Đang chờ câu hỏi"}
          </span>
          <Badge tone={speaking ? "accent" : "neutral"}>
            {words} từ
          </Badge>
        </div>
        <p className="mt-2 mb-0 line-clamp-4 text-[12px] leading-relaxed text-faint">
          {liveText || fullText.slice(-220) || "Chưa có nội dung nhận dạng."}
        </p>
      </PanelSection>

      <PanelSection title="Câu hỏi khớp">
        {lastAnswer?.matched ? (
          <div className="space-y-1.5">
            <p className="m-0 text-[12.5px] leading-relaxed text-white">
              {lastAnswer.matched.question}
            </p>
            <div className="flex items-center gap-1.5">
              <Badge tone="ok">{lastAnswer.matched.percent}%</Badge>
              {lastAnswer.matched.category && (
                <Badge tone="dim">{lastAnswer.matched.category}</Badge>
              )}
            </div>
          </div>
        ) : lastAnswer ? (
          <p className="m-0 text-[12px] leading-relaxed text-faint">
            Câu hỏi chưa có trong kho. Đã ghi vào danh sách “chưa trả lời” để bạn
            bổ sung ở trang Kho câu hỏi.
          </p>
        ) : (
          <p className="m-0 text-[12px] text-faint">
            Chưa có lượt hỏi nào trong phiên này.
          </p>
        )}

        {lastAnswer?.candidates?.length > 0 && (
          <div className="mt-2 space-y-1">
            {lastAnswer.candidates.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => handleAsk(item.question, "typed")}
                className="block w-full truncate rounded-lg px-2 py-1 text-left text-[11.5px] text-dim transition hover:bg-white/[0.06] hover:text-white"
              >
                {item.question} · {item.percent}%
              </button>
            ))}
          </div>
        )}
      </PanelSection>

      <PanelSection title="Đang đọc">
        {speech.busy ? (
          <div className="space-y-1.5">
            <p className="m-0 text-[12px] text-white">
              {speech.status === "loading" ? "Đang tổng hợp…" : "Đang đọc câu trả lời"}
            </p>
            <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-gradient-to-r from-accent to-accent-2"
                style={{ width: `${Math.round(speech.progress * 100)}%` }}
              />
            </div>
            <p className="m-0 font-mono text-[10.5px] text-faint">
              {speech.seconds.toFixed(1)} s
              {speech.estimated ? ` / ~${Math.round(speech.estimated)} s` : ""}
            </p>
          </div>
        ) : (
          <p className="m-0 text-[12px] text-faint">
            Bấm “Đọc” ở câu trả lời để nghe. Audio được tạo theo luồng, không chờ
            hết văn bản.
          </p>
        )}
      </PanelSection>
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
      <Thread
        turns={turns}
        onExample={(example) => handleAsk(example, "typed")}
        renderAnswerProps={(turn) => ({
          active: readingId === turn.answer?.id,
          playing: speech.busy && readingId === turn.answer?.id,
          progress: speech.progress,
          seconds: speech.seconds,
          estimated: speech.estimated,
          downloadUrl:
            readingId === turn.answer?.id ? speech.downloadUrl : "",
          onRead: () => read(turn.answer),
          onStop: stopReading,
          onPick: (question) => handleAsk(question, "typed"),
        })}
      />

      {error && (
        <p className="mx-5 mb-2 rounded-lg border border-err/35 bg-err/10 px-3 py-2 text-[12px] text-err">
          {error}
        </p>
      )}

      <Composer
        onAsk={handleAsk}
        busy={busy}
        suggestion={suggestion}
        onDismissSuggestion={dismiss}
      />
    </AppShell>
  );
}
