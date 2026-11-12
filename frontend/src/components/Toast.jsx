import { useEffect, useState } from "react";

import { useApp } from "../context/AppContext";

export default function Toast() {
  const { toast } = useApp();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!toast.text) return undefined;
    setVisible(true);
    const timer = window.setTimeout(() => setVisible(false), 1800);
    return () => window.clearTimeout(timer);
  }, [toast.id, toast.text]);

  return (
    <div
      role="status"
      aria-live="polite"
      className={`pointer-events-none fixed bottom-7 left-1/2 z-[60] -translate-x-1/2 rounded-full border border-line bg-surface-2 px-4 py-2 text-sm shadow-lg transition-opacity duration-200 ${
        visible ? "opacity-100" : "opacity-0"
      }`}
    >
      {toast.text}
    </div>
  );
}
