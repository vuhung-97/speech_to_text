// "Nghe" is one deliberate press, not a background microphone.
//
// start(): open the browser mic + WebSocket session. Every finalized sentence is
// handed to onText *immediately* (the input grows while you keep speaking);
// after GRACE_MS without new speech the mic closes and only the unfinished tail
// (live partial) is handed over. The timer restarts on new finals and on live
// loudness, so continuing to speak extends the session. A hard limit protects
// against a microphone left open by mistake.

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

import { useSpeechStream } from "../mic/useSpeechStream";
import {
  GRACE_MS,
  HARD_LIMIT_MS,
  INITIAL_GRACE_MS,
  SPEECH_LEVEL,
} from "../mic/constants";

export function useListen({ onText } = {}) {
  const stream = useSpeechStream();
  const [active, setActive] = useState(false);

  const activeRef = useRef(false);
  const baselineRef = useRef(0);
  const pendingRef = useRef([]);
  const graceRef = useRef(0);
  const hardRef = useRef(0);
  const onTextRef = useRef(onText);
  const liveRef = useRef(stream.live);
  const finishRef = useRef(() => Promise.resolve(""));

  // The stream object is rebuilt every render; keep the stable pieces in refs so
  // effects never tear down a live microphone just because React re-rendered.
  const startMicRef = useRef(stream.start);
  const stopMicRef = useRef(stream.stop);
  const clearStreamRef = useRef(stream.clear);
  const lastFinalRef = useRef(stream.lastFinal);

  useEffect(() => {
    startMicRef.current = stream.start;
    stopMicRef.current = stream.stop;
    clearStreamRef.current = stream.clear;
    lastFinalRef.current = stream.lastFinal;
    liveRef.current = stream.live;
    onTextRef.current = onText;
  }, [stream.start, stream.stop, stream.clear, stream.lastFinal, stream.live, onText]);

  const clearTimers = useCallback(() => {
    if (graceRef.current) window.clearTimeout(graceRef.current);
    if (hardRef.current) window.clearTimeout(hardRef.current);
    graceRef.current = 0;
    hardRef.current = 0;
  }, []);

  const deliver = useCallback((text) => {
    const value = (text || "").trim();
    if (!value) return;
    const callback = onTextRef.current;
    if (callback) callback(value);
    else pendingRef.current.push(value);
  }, []);

  const finish = useCallback(async () => {
    if (!activeRef.current) return "";
    activeRef.current = false;
    clearTimers();
    setActive(false);

    const live = liveRef.current;
    const tail = `${live.stable || ""} ${live.tentative || ""}`.trim();
    await stopMicRef.current();

    if (!onTextRef.current) {
      // No consumer: keep the legacy "full transcript on stop" behaviour.
      const heard = pendingRef.current.join(" ").trim();
      pendingRef.current = [];
      return heard || tail;
    }
    deliver(tail);
    return tail;
  }, [clearTimers, deliver]);

  useEffect(() => {
    finishRef.current = finish;
  }, [finish]);

  const armGrace = useCallback(() => {
    if (graceRef.current) window.clearTimeout(graceRef.current);
    graceRef.current = window.setTimeout(() => {
      finishRef.current();
    }, GRACE_MS);
  }, []);

  const start = useCallback(async (deviceId) => {
    if (activeRef.current) return;
    clearStreamRef.current();
    pendingRef.current = [];
    baselineRef.current = lastFinalRef.current.seq;
    const opened = await startMicRef.current(deviceId);
    if (!opened) return;
    activeRef.current = true;
    setActive(true);
    // Two timers: a silence grace that restarts while the server hears speech,
    // and a hard cap so the microphone can never stay open forever. The first
    // grace is longer, to give the speaker time to start.
    graceRef.current = window.setTimeout(() => {
      finishRef.current();
    }, INITIAL_GRACE_MS);
    hardRef.current = window.setTimeout(() => {
      finishRef.current();
    }, HARD_LIMIT_MS);
  }, [armGrace]);

  // A finalized sentence belongs to this session only if it arrived after start.
  // useLayoutEffect so the input never shows a frame missing the just-finalized
  // sentence (the partial was cleared by the same event that finalized it).
  useLayoutEffect(() => {
    if (!active) return;
    if (stream.lastFinal.seq <= baselineRef.current) return;
    baselineRef.current = stream.lastFinal.seq;
    deliver(stream.lastFinal.text);
    armGrace();
  }, [active, stream.lastFinal.seq, stream.lastFinal.text, deliver, armGrace]);

  // Still talking? Use the client-side RMS, not the partial text: ambient noise
  // can keep producing drafts forever in realtime mode, while real speech is
  // clearly louder than the room.
  useEffect(() => {
    if (!active) return;
    if (stream.level < SPEECH_LEVEL) return;
    armGrace();
  }, [active, stream.level, armGrace]);

  // Leaving the screen must never leave the microphone open.
  useEffect(
    () => () => {
      clearTimers();
      if (activeRef.current) {
        activeRef.current = false;
        stopMicRef.current();
      }
    },
    [clearTimers],
  );

  return {
    active,
    error: stream.error,
    notice: stream.notice,
    micState: stream.state,
    live: stream.live,
    level: stream.level,
    packets: stream.packets,
    deviceLabel: stream.deviceLabel,
    sampleRate: stream.sampleRate,
    start,
    stop: finish,
  };
}
