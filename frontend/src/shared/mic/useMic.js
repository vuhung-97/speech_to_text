// Browser microphone → WebSocket PCM16. One session per call, fully client-side
// device ownership: `stop()` stops the track so the OS microphone light goes off.

import { useCallback, useEffect, useRef, useState } from "react";

import {
  MIC_RATE,
  PACKET_SECONDS,
  WS_AUDIO_PATH,
  WORKLET_URL,
} from "./constants";

function socketUrl() {
  const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${scheme}//${window.location.host}${WS_AUDIO_PATH}`;
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

      const ws = new WebSocket(socketUrl());
      ws.binaryType = "arraybuffer";
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
        const reasons = {
          1003: "định dạng audio không được hỗ trợ",
          1008: "origin của trang bị máy chủ từ chối",
          1012: "cài đặt vừa thay đổi — bấm Nghe lại",
          1013: "máy chủ đang bận (đủ phiên) — thử lại sau",
        };
        setError(reasons[event.code] || "mất kết nối tới máy chủ nhận dạng");
      };

      try {
        await new Promise((resolve, reject) => {
          ws.onopen = resolve;
          ws.onerror = () => reject(new Error("không kết nối được máy chủ"));
        });

        if (!navigator.mediaDevices?.getUserMedia) {
          throw new Error(
            window.isSecureContext
              ? "trình duyệt không hỗ trợ micro"
              : "trang chưa chạy HTTPS — micro bị chặn (xem docs/TRIEN_KHAI_LAN.md)",
          );
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
        // AudioContext once the page is capturing audio. Creating it earlier
        // leaves it suspended and the worklet never runs.
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        const tracks = stream.getAudioTracks();
        tracks.forEach((track) => {
          track.enabled = true;
        });
        setDeviceLabel(tracks[0]?.label || "");

        let context;
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
        node.onprocessorerror = () => {
          setState("error");
          setError("bộ xử lý âm thanh (worklet) gặp lỗi");
        };

        if (context.state !== "running") await context.resume().catch(() => {});
        if (context.state !== "running") {
          throw new Error("trình duyệt đang chặn âm thanh — bấm Nghe lại");
        }
        setSampleRate(context.sampleRate);

        node.port.onmessage = (event) => {
          const payload = event.data;
          if (payload.type === "audio") {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(payload.buffer);
              packetsRef.current += 1;
              if (packetsRef.current % 25 === 0) {
                setPackets(packetsRef.current);
              }
            }
          } else if (payload.type === "level") {
            setLevel(payload.value);
          }
        };

        refs.current = { ws, stream, context, source, node, mute };
        setupRef.current = true;
        markLive();
        return true;
      } catch (startError) {
        await teardown();
        setState("error");
        setError(
          startError?.name === "NotAllowedError"
            ? "bạn chưa cho phép dùng micro"
            : startError?.message || "không mở được micro",
        );
        return false;
      }
    },
    [teardown],
  );

  useEffect(() => () => { teardown(); }, [teardown]);

  return { state, level, packets, deviceLabel, sampleRate, error, start, stop };
}

export default useMic;
