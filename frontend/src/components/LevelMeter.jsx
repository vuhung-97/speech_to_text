// Smoothed microphone meter: display only, driven by rAF.
// The level comes from the browser worklet, not from the server.

import { useEffect, useRef } from "react";

export default function LevelMeter({ level = 0, speaking = false }) {
  const fill = useRef(null);
  const target = useRef(0);
  const shown = useRef(0);
  target.current = level;

  useEffect(() => {
    let frame = 0;
    const tick = () => {
      shown.current += (target.current - shown.current) * 0.22;
      const ratio = Math.min(1, Math.pow(Math.max(0, shown.current) * 13, 0.55));
      if (fill.current) {
        fill.current.style.transform = `scaleX(${ratio.toFixed(3)})`;
      }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <div className="h-1 w-full overflow-hidden rounded-full bg-white/10" aria-hidden="true">
      <div
        ref={fill}
        className={`h-full origin-left rounded-full bg-gradient-to-r from-accent-2 to-accent transition-opacity ${
          speaking ? "opacity-100" : "opacity-60"
        }`}
        style={{ transform: "scaleX(0)" }}
      />
    </div>
  );
}
