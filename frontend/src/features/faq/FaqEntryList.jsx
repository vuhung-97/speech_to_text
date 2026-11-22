import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import EmptyState from "../../components/ui/EmptyState";

function PrerenderButton({ job, disabled, onClick }) {
  if (job?.status === "running") {
    return (
      <Button variant="ghost" size="sm" disabled>
        Đang tạo…
      </Button>
    );
  }
  if (job?.status === "done") {
    return (
      <Button variant="ghost" size="sm" disabled>
        Đã lưu bản đọc
      </Button>
    );
  }
  return (
    <Button variant="ghost" size="sm" onClick={onClick} disabled={disabled}>
      Tổng hợp sẵn
    </Button>
  );
}

function ListSkeleton() {
  return (
    <div className="space-y-2" aria-busy="true">
      {[0, 1, 2].map((item) => (
        <div
          key={item}
          className="animate-pulse rounded-xl border border-line bg-wash p-4 motion-reduce:animate-none"
        >
          <div className="h-4 w-2/3 rounded bg-wash-hover" />
          <div className="mt-2 h-3 w-full rounded bg-wash-strong" />
        </div>
      ))}
    </div>
  );
}

export default function FaqEntryList({
  entries,
  jobs,
  busy,
  loading,
  onEdit,
  onToggle,
  onPrerender,
  onRemove,
  emptyTitle = "Kho đang trống",
  emptyHint = "Thêm câu hỏi ở trên hoặc nhập tệp .docx/CSV.",
}) {
  if (loading && !entries.length) return <ListSkeleton />;

  if (!loading && !entries.length) {
    return <EmptyState title={emptyTitle} hint={emptyHint} />;
  }

  return (
    <div className="space-y-2">
      {entries.map((entry) => (
        <article
          key={entry.id}
          className="rounded-xl border border-line bg-wash p-3.5 transition hover:bg-wash-strong"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <p className="m-0 text-[12.5px] font-medium leading-relaxed text-content">
                {entry.question}
              </p>
              <p className="mt-1 mb-0 line-clamp-2 text-[10.8px] leading-relaxed text-faint">
                {entry.answer}
              </p>
            </div>
            <div className="flex max-w-[42%] shrink-0 flex-wrap items-center justify-end gap-1">
              {entry.source_ref && (
                <Badge tone="neutral" title={entry.source_file || ""}>
                  {entry.source_ref}
                </Badge>
              )}
              {entry.category && <Badge tone="dim">{entry.category}</Badge>}
              <Badge tone={entry.active ? "ok" : "neutral"}>
                {entry.active ? "Bật" : "Tắt"}
              </Badge>
            </div>
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-0.5">
            <Button variant="ghost" size="sm" onClick={() => onEdit(entry)}>
              Sửa
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onToggle(entry)}
              disabled={busy}
            >
              {entry.active ? "Tắt" : "Bật"}
            </Button>
            <PrerenderButton
              job={jobs[entry.id]}
              disabled={busy}
              onClick={() => onPrerender(entry)}
            />
            <Button
              variant="ghost"
              size="sm"
              className="text-err hover:bg-err/10 hover:text-err"
              onClick={() => onRemove(entry)}
              disabled={busy}
            >
              Xoá
            </Button>
          </div>
        </article>
      ))}
    </div>
  );
}
