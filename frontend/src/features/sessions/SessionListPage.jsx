// Session history: the deep-linked list behind the "Phiên" rail item.

import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

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
    return new Date(value * 1000).toLocaleString("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

export default function SessionListPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
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

  return (
    <AppShell
      title="Phiên hội thoại"
      subtitle={loading ? "Đang tải…" : `${items.length} phiên trên máy này`}
      actions={
        <Button variant="secondary" size="sm" onClick={load} disabled={loading}>
          Làm mới
        </Button>
      }
    >
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-5 py-5">
        {error && <Alert className="mx-auto mb-3 max-w-[820px]">{error}</Alert>}

        {!loading && !items.length && !error && (
          <div className="mx-auto max-w-[720px]">
            <EmptyState
              title="Chưa có phiên nào"
              hint="Mỗi câu hỏi bạn gửi sẽ tạo một phiên gồm câu hỏi, câu trả lời khớp và phần giọng đọc."
              action={
                <Link
                  to="/"
                  className="inline-flex rounded-control bg-gradient-to-br from-accent to-accent-2 px-3.5 py-2 text-[13px] font-semibold text-[#201505]"
                >
                  Hỏi câu đầu tiên
                </Link>
              }
            />
          </div>
        )}

        <ul className="mx-auto m-0 flex max-w-[820px] list-none flex-col gap-2 p-0">
          {items.map((session) => (
            <li key={session.id}>
              <div className="flex items-center gap-3 rounded-card border border-line bg-surface-2/60 px-4 py-3">
                <button
                  type="button"
                  onClick={() => navigate(`/sessions/${session.id}`)}
                  className="min-w-0 flex-1 text-left"
                >
                  <p className="m-0 truncate text-[13.5px] text-white">
                    {session.first_question || session.title || "Phiên không tên"}
                  </p>
                  <p className="m-0 mt-1 flex items-center gap-2 text-[11px] text-faint">
                    <span>{when(session.updated_at)}</span>
                    <span aria-hidden="true">·</span>
                    <span>{session.turns} lượt</span>
                    <span aria-hidden="true">·</span>
                    <span className="font-mono">{session.id.slice(0, 8)}</span>
                  </p>
                </button>
                <Badge tone="dim">{session.turns} lượt</Badge>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => remove(session)}
                  disabled={deleting === session.id}
                >
                  {deleting === session.id ? "Đang xoá…" : "Xoá"}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </AppShell>
  );
}
