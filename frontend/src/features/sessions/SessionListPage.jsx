// Session history: the deep-linked list behind the "Phiên" rail item.

import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import AppShell from "../../app/AppShell";
import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import EmptyState from "../../components/ui/EmptyState";
import LinkButton from "../../components/ui/LinkButton";
import SearchInput from "../../components/ui/SearchInput";
import * as api from "../../services/api";
import { messageFor } from "../../services/errors";
import { filterSessions, groupSessions, when } from "./sessionList";

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

  const filtered = useMemo(() => filterSessions(items, query), [items, query]);
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
              <LinkButton to="/" className="shadow-accent">
                Hỏi câu mới
              </LinkButton>
            </div>
          </div>

          <div className="mb-5 flex items-center gap-2">
            <SearchInput
              label="Tìm phiên"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Tìm theo câu hỏi…"
              className="flex-1"
            />
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
                  <LinkButton to="/">Hỏi câu đầu tiên</LinkButton>
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
                      className="min-w-0 flex-1 rounded-md text-left focus-ring"
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
                      className="grid h-11 w-11 shrink-0 place-items-center rounded-lg text-faint transition hover:bg-err/10 hover:text-err focus-ring disabled:opacity-40 sm:h-9 sm:w-9"
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
