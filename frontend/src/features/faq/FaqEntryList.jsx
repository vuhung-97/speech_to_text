import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import EmptyState from "../../components/ui/EmptyState";

const SAMPLE_CSV = "question,answer,category\nThủ đô Việt Nam là gì?,Hà Nội.,địa lý\n";

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
    <ul className="m-0 flex list-none flex-col gap-2 p-0" aria-busy="true">
      {[0, 1, 2].map((item) => (
        <li
          key={item}
          className="animate-pulse rounded-card border border-line bg-surface-2/60 px-4 py-3 motion-reduce:animate-none"
        >
          <div className="h-4 w-2/3 rounded bg-white/[0.06]" />
          <div className="mt-2 h-3 w-full rounded bg-white/[0.04]" />
        </li>
      ))}
    </ul>
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
}) {
  if (loading && !entries.length) return <ListSkeleton />;

  if (!loading && !entries.length) {
    return (
      <EmptyState
        title="Kho đang trống"
        hint={`Thêm câu hỏi ở trên, hoặc nhập đề cương .docx (mỗi câu: dòng «Câu …», bảng câu hỏi/«Đáp án»), hoặc CSV 3 cột question, answer, category. Mẫu: ${SAMPLE_CSV.split("\n")[1]}`}
      />
    );
  }

  return (
    <ul className="m-0 flex list-none flex-col gap-2 p-0">
      {entries.map((entry) => (
        <li
          key={entry.id}
          className="rounded-card border border-line bg-surface-2/60 px-4 py-3"
        >
          <div className="flex items-start gap-3">
            <div className="min-w-0 flex-1">
              <p className="m-0 text-[13.5px] font-medium text-white">
                {entry.question}
              </p>
              <p className="mt-1 mb-0 line-clamp-2 text-[12px] leading-relaxed text-faint">
                {entry.answer}
              </p>
            </div>
            <div className="flex max-w-[45%] shrink-0 flex-wrap items-center justify-end gap-1.5">
              {entry.source_ref && (
                <Badge tone="neutral" title={entry.source_file || ""}>
                  {entry.source_ref}
                </Badge>
              )}
              {entry.category && <Badge tone="dim">{entry.category}</Badge>}
              <Badge tone={entry.active ? "ok" : "neutral"}>
                {entry.active ? "bật" : "tắt"}
              </Badge>
            </div>
          </div>
          <div className="mt-2 flex items-center gap-1.5">
            <Button variant="ghost" size="sm" onClick={() => onEdit(entry)}>
              Sửa
            </Button>
            <Button variant="ghost" size="sm" onClick={() => onToggle(entry)} disabled={busy}>
              {entry.active ? "Tắt" : "Bật"}
            </Button>
            <PrerenderButton
              job={jobs[entry.id]}
              disabled={busy}
              onClick={() => onPrerender(entry)}
            />
            <Button variant="danger" size="sm" onClick={() => onRemove(entry)} disabled={busy}>
              Xoá
            </Button>
          </div>
        </li>
      ))}
    </ul>
  );
}
