// Catalogue admin, phase 1: the "unanswered" worklist that P3 records.
// CRUD + import + reindex arrive with the embedding index (P5).

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import AppShell from "../../app/AppShell";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import EmptyState from "../../components/ui/EmptyState";
import * as api from "../../services/api";
import { messageFor } from "../../services/errors";

export default function FaqAdminPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getUnanswered();
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

  return (
    <AppShell
      title="Kho câu hỏi"
      subtitle="Câu hỏi người dùng đã hỏi mà kho chưa có đáp án"
      actions={
        <Button variant="secondary" size="sm" onClick={load} disabled={loading}>
          Làm mới
        </Button>
      }
    >
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-5 py-5">
        <div className="mx-auto max-w-[820px] space-y-4">
          <div className="rounded-card border border-accent/30 bg-accent/[0.07] px-4 py-3 text-[12.5px] leading-relaxed text-accent">
            Kho câu trả lời (thêm/sửa/nhập CSV/embedding) mở ở giai đoạn P5. Hiện
            tại mọi câu hỏi đều được ghi vào danh sách dưới đây để bạn soạn đáp án.
          </div>

          {error && (
            <p className="m-0 rounded-lg border border-err/35 bg-err/10 px-3 py-2 text-[12px] text-err">
              {error}
            </p>
          )}

          {!loading && !items.length && !error && (
            <EmptyState
              title="Chưa có câu hỏi nào chưa trả lời"
              hint="Khi người dùng hỏi một câu chưa có trong kho, câu đó xuất hiện ở đây kèm số lần hỏi."
              action={
                <Link
                  to="/"
                  className="inline-flex rounded-control bg-gradient-to-br from-accent to-accent-2 px-3.5 py-2 text-[13px] font-semibold text-[#201505]"
                >
                  Thử hỏi một câu
                </Link>
              }
            />
          )}

          {!!items.length && (
            <ul className="m-0 flex list-none flex-col gap-2 p-0">
              {items.map((item) => (
                <li
                  key={item.question_norm}
                  className="flex items-center gap-3 rounded-card border border-line bg-surface-2/60 px-4 py-3"
                >
                  <div className="min-w-0 flex-1">
                    <p className="m-0 truncate text-[13.5px] text-white">
                      {item.sample || item.question_norm}
                    </p>
                    <p className="m-0 mt-1 text-[11px] text-faint">
                      chuẩn hoá: <span className="font-mono">{item.question_norm}</span>
                    </p>
                  </div>
                  <Badge tone="accent">{item.asks} lần hỏi</Badge>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </AppShell>
  );
}
