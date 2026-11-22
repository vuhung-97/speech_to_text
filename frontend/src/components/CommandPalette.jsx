// Command palette (Ctrl+K): jump to a screen without leaving the keyboard.

import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useFocusTrap } from "./ui/useFocusTrap";

const ITEMS = [
  { to: "/", label: "Hỏi đáp" },
  { to: "/sessions", label: "Phiên hội thoại" },
  { to: "/faq", label: "Kho câu hỏi" },
];

export default function CommandPalette({ open, onClose }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState(0);
  const inputRef = useRef(null);
  const dialogRef = useRef(null);
  useFocusTrap(dialogRef, open, onClose);

  const items = useMemo(() => {
    const value = query.trim().toLowerCase();
    if (!value) return ITEMS;
    return ITEMS.filter((item) => item.label.toLowerCase().includes(value));
  }, [query]);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setIndex(0);
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setIndex((current) => Math.min(current + 1, items.length - 1));
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        setIndex((current) => Math.max(current - 1, 0));
      } else if (event.key === "Enter" && items[index]) {
        event.preventDefault();
        navigate(items[index].to);
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, items, index, navigate, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-start justify-center bg-black/60 px-4 pt-[12vh] backdrop-blur-[2px]"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Điều hướng nhanh"
        tabIndex={-1}
        className="w-[min(520px,100%)] overflow-hidden rounded-card border border-line bg-surface-2 shadow-[0_40px_120px_-40px_#000] outline-none"
      >
        <input
          ref={inputRef}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setIndex(0);
          }}
          placeholder="Đi tới…"
          aria-label="Tìm màn hình"
          className="w-full border-b border-line bg-transparent px-4 py-3 text-[14px] text-white outline-none placeholder:text-faint focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-accent sm:text-[13.5px]"
        />
        <ul role="listbox" aria-label="Màn hình" className="m-0 max-h-[320px] list-none overflow-y-auto p-1.5">
          {items.map((item, position) => (
            <li key={item.to} role="option" aria-selected={position === index}>
              <button
                type="button"
                onMouseEnter={() => setIndex(position)}
                onClick={() => {
                  navigate(item.to);
                  onClose();
                }}
                className={`flex min-h-11 w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:min-h-0 ${
                  position === index
                    ? "bg-accent/15 text-white"
                    : "text-dim hover:bg-white/[0.05]"
                }`}
              >
                <span className="text-[13px]">{item.label}</span>
              </button>
            </li>
          ))}
          {!items.length && (
            <li className="px-3 py-4 text-center text-[12px] text-faint">
              Không có màn hình khớp.
            </li>
          )}
        </ul>
      </div>
    </div>
  );
}
