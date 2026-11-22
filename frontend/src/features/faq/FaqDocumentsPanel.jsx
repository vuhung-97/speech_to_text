// Question sets: name, entry count, rename and delete. Presentational only.

import Button from "../../components/ui/Button";

function timeLabel(value) {
  if (!value) return "";
  try {
    return new Date(value * 1000).toLocaleDateString("vi-VN");
  } catch {
    return "";
  }
}

export default function FaqDocumentsPanel({ documents, busy, onRename, onRemove }) {
  return (
    <section className="mb-4 rounded-xl border border-line bg-wash p-3">
      <h2 className="m-0 mb-2 text-[12px] font-semibold tracking-[0.08em] text-faint uppercase">
        Bộ đề
      </h2>
      {documents.length === 0 ? (
        <p className="m-0 text-[12px] text-faint">
          Chưa có bộ đề nào — bấm “Nhập câu hỏi” và chọn tệp .docx.
        </p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {documents.map((document) => (
            <li
              key={document.id}
              className="flex items-center justify-between gap-2 rounded-lg border border-line bg-wash-strong px-2.5 py-2"
            >
              <div className="min-w-0">
                <p className="m-0 truncate text-[12.5px] text-content">{document.name}</p>
                <p className="m-0 text-[12px] text-faint">
                  {document.entry_count} câu · {timeLabel(document.updated_at)}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onRename(document)}
                  disabled={busy}
                >
                  Đổi tên
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => onRemove(document)}
                  disabled={busy}
                >
                  Xoá
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
