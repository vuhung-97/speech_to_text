// App-level UI notifications. Kept separate from server state so settings and
// dictation features can both raise a toast without depending on each other.

import { createContext, useCallback, useContext, useMemo, useState } from "react";

const ToastContext = createContext(null);

export const useToast = () => useContext(ToastContext);

export function ToastProvider({ children }) {
  const [toast, setToast] = useState({ id: 0, text: "" });

  const notify = useCallback((text) => {
    if (text) setToast({ id: Date.now(), text });
  }, []);

  const value = useMemo(() => ({ toast, notify }), [toast, notify]);

  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}
