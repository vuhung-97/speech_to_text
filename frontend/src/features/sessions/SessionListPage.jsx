// Session history: the deep-linked list behind the "Phiên" rail item.

import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import AppShell from "../../app/AppShell";
import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import EmptyState from "../../components/ui/EmptyState";
import * as api from "../../services/api";
import { messageFor } from "../../services/errors";

function when(value) {
  if (!value) return "";
  try {
    return new Date(value * 1000).toLocaleTimeString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

function dayLabel(value) {
  if (!value) return "Trước đó";
  const date = new Date(value * 1000);
  if (Number.isNaN(date.getTime())) return "Trước đó";
  const today = new Date();
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const days = Math.round((start - target) / 86_400_000);
  if (days === 0) return "Hôm nay";
  if (days === 1) return "Hôm qua";
  return "Trước đó";
}

function groupSessions(items) {
  const groups = [];
  for (const item of items) {
    const label = dayLabel(item.updated_at);
    let group = groups.find((entry) => entry.label === label);
    if (!group) {
      group = { label, items: [] };
      groups.push(group);
    }
    group.items.push(item);
  }
  return groups;
}

function SearchIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      aria-hidden="true"
      className="h-3.5 w-3.5"
    >
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.4-3.4" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="h-3.5 w-3.5"
    >
      <path d="M21 15a3 3 0 0 1-3 3H8l-5 3V6a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3z" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="h-3.5 w-3.5"
    >
      <path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" />
    </svg>
  );
}

export default function SessionListPage() {
  const [items, setItems] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getSessions();
      setItems(data.items || []);
      setError("");
    } catch (loadError) {
      setError(messageFor(loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const remove = async (session) => {
    const label = session.first_question || session.title || session.id;
    if (!window.confirm(`Xoá phiên “${label}”? Thao tác này không hoàn tác.`)) {
      return;
    }
    setDeleting(session.id);
    try {
      await api.deleteSession(session.id);
      setItems((previous) => previous.filter((item) => item.id !== session.id));
    } catch (deleteError) {
      setError(messageFor(deleteError));
    } finally {
      setDeleting("");
    }
  };

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return items;
    return items.filter((item) =>
      [item.first_question, item.title, item.id]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(needle)),
    );
  }, [items, query]);

  const groups = useMemo(() => groupSessions(filtered), [filtered]);

  return (
    <AppShell
      title="Phiên hội thoại"
      subtitle={
        loading ? "Đang tải…" : `${items.length} phiên trên máy này`
      }
    >
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-[900px]">
          <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="m-0 text-[22px] font-semibold tracking-[-0.035em] sm:text-[23px]">
                Phiên hội thoại
              </h2>
              <p className="m-0 mt-1 text-[11.5px] text-faint">
                Câu hỏi đã hỏi và câu trả lời tương ứng.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={load}
                disabled={loading}
              >
                Làm mới
              </Button>
              <Link
                to="/"
                className="inline-flex min-h-11 items-center rounded-control bg-gradient-to-br from-accent to-accent-2 px-3.5 py-2 text-[11.5px] font-semibold text-on-accent shadow-accent transition hover:brightness-110 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:min-h-0"
              >
                Hỏi câu mới
              </Link>
            </div>
          </div>

          <div className="mb-5 flex items-center gap-2">
            <label className="flex min-h-11 min-w-0 flex-1 items-center gap-2 rounded-control border border-line bg-wash-strong px-3 py-2 focus-within:border-accent/60 sm:min-h-0">
              <SearchIcon />
              <span className="sr-only">Tìm phiên</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Tìm theo câu hỏi…"
                className="w-full min-w-0 border-0 bg-transparent text-[12px] text-content outline-none placeholder:text-faint"
              />
            </label>
            <span className="shrink-0 text-[10.5px] text-faint">
              {filtered.length} phiên
            </span>
          </div>

          {error && <Alert className="mb-3">{error}</Alert>}

          {loading && !items.length && (
            <div className="space-y-2" aria-busy="true">
              {[0, 1, 2, 3].map((item) => (
                <div
                  key={item}
                  className="h-14 animate-pulse rounded-xl border border-line bg-wash-strong motion-reduce:animate-none"
                />
              ))}
            </div>
          )}

          {!loading && !filtered.length && !error && (
            <EmptyState
              title={query ? "Không tìm thấy phiên" : "Chưa có phiên nào"}
              hint={
                query
                  ? "Thử từ khoá khác hoặc xoá bộ lọc tìm kiếm."
                  : "Câu hỏi đã hỏi và câu trả lời tương ứng."
              }
              action={
                !query && (
                  <Link
                    to="/"
                    className="inline-flex min-h-11 items-center rounded-control bg-gradient-to-br from-accent to-accent-2 px-3.5 py-2 text-[13px] font-semibold text-on-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:min-h-0"
                  >
                    Hỏi câu đầu tiên
                  </Link>
                )
              }
            />
          )}

          {groups.map((group, index) => (
            <section key={group.label}>
              <h3
                className={`mb-2 flex items-center gap-2.5 text-[10px] font-semibold tracking-[0.12em] text-faint uppercase ${
                  index === 0 ? "mt-0" : "mt-5"
                }`}
              >
                {group.label}
                <span className="h-px flex-1 bg-line" aria-hidden="true" />
              </h3>
              <div>
                {group.items.map((session) => (
                  <div
                    key={session.id}
                    className="-mx-2 flex items-center gap-3 rounded-lg border-b border-line px-2 py-3.5 transition last:border-b-0 hover:bg-wash"
                  >
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-line bg-wash-strong text-faint">
                      <ChatIcon />
                    </span>
                    <Link
                      to={`/sessions/${session.id}`}
                      className="min-w-0 flex-1 rounded-md text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                    >
                      <span className="block truncate text-[12.5px] font-medium text-content">
                        {session.first_question || session.title || "Phiên không tên"}
                      </span>
                      <span className="mt-1 block text-[10.5px] text-faint">
                        {when(session.updated_at)} · {session.turns} lượt
                      </span>
                    </Link>
                    <Badge tone="dim" className="hidden sm:inline-flex">
                      {session.turns} lượt
                    </Badge>
                    <button
                      type="button"
                      onClick={() => remove(session)}
                      disabled={deleting === session.id}
                      aria-label={`Xoá phiên ${
                        session.first_question || session.title || session.id
                      }`}
                      title="Xoá phiên"
                      className="grid h-11 w-11 shrink-0 place-items-center rounded-lg text-faint transition hover:bg-err/10 hover:text-err focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-40 sm:h-9 sm:w-9"
                    >
                      <TrashIcon />
                    </button>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
