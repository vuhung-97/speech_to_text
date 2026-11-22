// Browser microphone → WebSocket PCM16. One session per call, fully client-side
// device ownership: `stop()` stops the track so the OS microphone light goes off.

import { useCallback, useEffect, useRef, useState } from "react";

import {
  MIC_RATE,
  PACKET_SECONDS,
  WS_AUDIO_PATH,
  WORKLET_URL,
} from "./constants";
import { closeReason, missingDeviceMessage, startErrorMessage } from "./errors";

const PACKETS_PER_UI_UPDATE = 25;

function socketUrl() {
  const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${scheme}//${window.location.host}${WS_AUDIO_PATH}`;
}

function openSocket() {
  const ws = new WebSocket(socketUrl());
  ws.binaryType = "arraybuffer";
  return ws;
}

// Microphone → AudioWorklet graph. Releases the device itself when a step fails,
// so a rejected permission can never leave the OS microphone open.
async function openCapture(deviceId) {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error(missingDeviceMessage());
  }

  const constraints = {
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      ...(deviceId ? { deviceId: { exact: deviceId } } : {}),
    },
  };
  // Ask for the microphone first: Chrome's autoplay policy allows an
  // AudioContext once the page is capturing audio. Creating it earlier leaves
  // it suspended and the worklet never runs.
  const stream = await navigator.mediaDevices.getUserMedia(constraints);
  let context;
  try {
    const tracks = stream.getAudioTracks();
    tracks.forEach((track) => {
      track.enabled = true;
    });

    try {
      context = new AudioContext({ sampleRate: MIC_RATE });
    } catch {
      context = new AudioContext();
    }
    if (context.state !== "running") await context.resume().catch(() => {});
    await context.audioWorklet.addModule(WORKLET_URL);

    const source = context.createMediaStreamSource(stream);
    const node = new AudioWorkletNode(context, "pcm-processor", {
      processorOptions: { targetRate: MIC_RATE, packetSeconds: PACKET_SECONDS },
    });
    const mute = context.createGain();
    mute.gain.value = 0;
    source.connect(node);
    node.connect(mute);
    mute.connect(context.destination);

    if (context.state !== "running") await context.resume().catch(() => {});
    if (context.state !== "running") {
      throw new Error("trình duyệt đang chặn âm thanh — bấm Nghe lại");
    }

    return {
      stream,
      context,
      source,
      node,
      mute,
      label: tracks[0]?.label || "",
      sampleRate: context.sampleRate,
    };
  } catch (error) {
    stream.getTracks().forEach((track) => track.stop());
    if (context && context.state !== "closed") {
      await context.close().catch(() => {});
    }
    throw error;
  }
}

export function useMic({ onEvent } = {}) {
  const [state, setState] = useState("idle"); // idle | connecting | live | error
  const [level, setLevel] = useState(0);
  const [packets, setPackets] = useState(0);
  const [deviceLabel, setDeviceLabel] = useState("");
  const [sampleRate, setSampleRate] = useState(0);
  const [error, setError] = useState("");
  const refs = useRef({});
  const packetsRef = useRef(0);
  const readyRef = useRef(false);
  const setupRef = useRef(false);
  const onEventRef = useRef(onEvent);

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  const teardown = useCallback(async () => {
    const current = refs.current;
    refs.current = {};
    try {
      if (current.ws?.readyState === WebSocket.OPEN) {
        current.ws.send(JSON.stringify({ type: "stop" }));
      }
    } catch {
      /* socket already gone */
    }
    try {
      current.ws?.close();
    } catch {
      /* ignore */
    }
    try {
      current.node?.port.close();
    } catch {
      /* ignore */
    }
    try {
      current.source?.disconnect();
      current.node?.disconnect();
      current.mute?.disconnect();
    } catch {
      /* ignore */
    }
    current.stream?.getTracks().forEach((track) => track.stop());
    if (current.context && current.context.state !== "closed") {
      await current.context.close().catch(() => {});
    }
  }, []);

  const stop = useCallback(async () => {
    await teardown();
    packetsRef.current = 0;
    setPackets(0);
    setLevel(0);
    setState("idle");
  }, [teardown]);

  const start = useCallback(
    async (deviceId) => {
      if (refs.current.ws) return false;
      setError("");
      setState("connecting");
      packetsRef.current = 0;
      readyRef.current = false;
      setupRef.current = false;
      setPackets(0);

      const markLive = () => {
        if (readyRef.current && setupRef.current) setState("live");
      };

      const ws = openSocket();
      refs.current = { ws };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "ready") {
            readyRef.current = true;
            markLive();
          }
          onEventRef.current?.(payload);
        } catch {
          /* malformed frame */
        }
      };
      ws.onclose = (event) => {
        if (refs.current.ws !== ws) return;
        refs.current = {};
        setState("error");
        setError(closeReason(event.code));
      };

      try {
        await new Promise((resolve, reject) => {
          ws.onopen = resolve;
          ws.onerror = () => reject(new Error("không kết nối được máy chủ"));
        });

        const capture = await openCapture(deviceId);
        const { label, sampleRate: captureRate, ...parts } = capture;
        setDeviceLabel(label);
        setSampleRate(captureRate);

        capture.node.onprocessorerror = () => {
          setState("error");
          setError("bộ xử lý âm thanh (worklet) gặp lỗi");
        };
        capture.node.port.onmessage = (event) => {
          const payload = event.data;
          if (payload.type === "audio") {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(payload.buffer);
              packetsRef.current += 1;
              if (packetsRef.current % PACKETS_PER_UI_UPDATE === 0) {
                setPackets(packetsRef.current);
              }
            }
          } else if (payload.type === "level") {
            setLevel(payload.value);
          }
        };

        refs.current = { ws, ...parts };
        setupRef.current = true;
        markLive();
        return true;
      } catch (startError) {
        await teardown();
        setState("error");
        setError(startErrorMessage(startError));
        return false;
      }
    },
    [teardown],
  );

  useEffect(() => () => { teardown(); }, [teardown]);

  return { state, level, packets, deviceLabel, sampleRate, error, start, stop };
}

export default useMic;
