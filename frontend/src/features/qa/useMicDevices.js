import { useCallback, useEffect, useState } from "react";

import { MIC_STORAGE_KEY } from "../mic/constants";

// Browser input devices + the remembered choice. The server never lists
// microphones any more: each client owns its own.
export function useMicDevices() {
  const [devices, setDevices] = useState([]);
  const [device, setDevice] = useState(
    () => window.localStorage.getItem(MIC_STORAGE_KEY) || "",
  );

  const refresh = useCallback(async () => {
    try {
      const list = await navigator.mediaDevices?.enumerateDevices?.();
      setDevices((list || []).filter((item) => item.kind === "audioinput"));
    } catch {
      setDevices([]);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const choose = useCallback((value) => {
    setDevice(value);
    window.localStorage.setItem(MIC_STORAGE_KEY, value);
  }, []);

  return { devices, device, refresh, choose };
}
