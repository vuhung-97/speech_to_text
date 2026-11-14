// "Nghe" is one deliberate press, not a background microphone.
//
// start(): stop nothing here (the screen does that), clear the previous STT
// buffer, open the device. Every finalized sentence is collected; after two
// seconds without new speech the device closes and the text is handed over.
// The timer restarts on new finals and on live partial updates, so continuing
// to speak extends the session.

import { useCallback, useEffect, useRef, useState } from "react";

import * as api from "../../services/api";
import { messageFor } from "../../services/errors";
import { useLive } from "../dictation/LiveProvider";

const GRACE_MS = 2_000;      // silence after a sentence before closing the mic
const IDLE_LIMIT_MS = 30_000; // never hold the device open forever with no speech

export function useListen({ onText } = {}) {
  const { lastFinal, live } = useLive();
  const [active, setActive] = useState(false);
  const [error, setError] = useState("");

  const activeRef = useRef(false);
  const baselineRef = useRef(0);
  const chunksRef = useRef([]);
  const graceRef = useRef(0);
  const idleRef = useRef(0);
  const onTextRef = useRef(onText);
  const liveRef = useRef(live);
  const finishRef = useRef(() => Promise.resolve(""));

  useEffect(() => {
    onTextRef.current = onText;
  }, [onText]);

  useEffect(() => {
    liveRef.current = live;
  }, [live]);

  const clearTimers = useCallback(() => {
    if (graceRef.current) window.clearTimeout(graceRef.current);
    if (idleRef.current) window.clearTimeout(idleRef.current);
    graceRef.current = 0;
    idleRef.current = 0;
  }, []);

  const finish = useCallback(async () => {
    if (!activeRef.current) return "";
    activeRef.current = false;
    clearTimers();
    setActive(false);
    try {
      await api.setListening(false);
    } catch (stopError) {
      setError(messageFor(stopError));
    }

    const heard = chunksRef.current.join(" ").trim();
    chunksRef.current = [];
    const text = heard || `${liveRef.current.stable || ""} ${liveRef.current.tentative || ""}`.trim();
    if (text) onTextRef.current?.(text);
    return text;
  }, [clearTimers]);

  useEffect(() => {
    finishRef.current = finish;
  }, [finish]);

  const armGrace = useCallback(() => {
    if (graceRef.current) window.clearTimeout(graceRef.current);
    graceRef.current = window.setTimeout(() => {
      finishRef.current();
    }, GRACE_MS);
    if (idleRef.current) {
      window.clearTimeout(idleRef.current);
      idleRef.current = 0;
    }
  }, []);

  const start = useCallback(async () => {
    if (activeRef.current) return;
    setError("");
    chunksRef.current = [];
    baselineRef.current = lastFinal.seq;
    try {
      await api.clearTranscript();
      await api.setListening(true);
      activeRef.current = true;
      setActive(true);
      idleRef.current = window.setTimeout(() => {
        finishRef.current();
      }, IDLE_LIMIT_MS);
    } catch (startError) {
      setError(messageFor(startError));
    }
  }, [lastFinal.seq]);

  // A finalized sentence belongs to this session only if it arrived after start.
  useEffect(() => {
    if (!active) return;
    if (lastFinal.seq <= baselineRef.current) return;
    baselineRef.current = lastFinal.seq;
    if (lastFinal.text) chunksRef.current.push(lastFinal.text);
    armGrace();
  }, [active, lastFinal.seq, lastFinal.text, armGrace]);

  // Live partial text means the speaker is still going: keep the mic open.
  useEffect(() => {
    if (!active) return;
    if (!live.stable && !live.tentative) return;
    armGrace();
  }, [active, live.stable, live.tentative, armGrace]);

  // Closing the screen must never leave the device open.
  useEffect(
    () => () => {
      clearTimers();
      if (activeRef.current) {
        activeRef.current = false;
        api.setListening(false).catch(() => {});
      }
    },
    [clearTimers],
  );

  return { active, error, start, stop: finish };
}
