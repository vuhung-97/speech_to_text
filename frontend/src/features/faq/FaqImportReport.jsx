// Import result banner. CSV reports carry `duplicates`; outline reports carry
// `updated`/`skipped`. Rendering both from one place keeps the page presentational.

const LIMIT_ERRORS = 3;

function errorLine(item) {
  const where = item.code || (item.row ? `dòng ${item.row}` : "");
  return `${where ? `${where}: ` : ""}${item.error}`;
}

export default function FaqImportReport({ report }) {
  if (!report) return null;

  const duplicates = report.duplicates?.length || 0;
  const updated = report.updated || 0;
  const skipped = report.skipped || 0;
  const errors = report.errors || [];

  return (
    <div
      className="rounded-lg border border-ok/30 bg-ok/[0.08] px-3 py-2 text-[12px] text-ok"
      aria-live="polite"
    >
      Đã thêm {report.added ?? 0}/{report.total ?? 0} câu
      {updated > 0 && ` · cập nhật ${updated}`}
      {duplicates > 0 && ` · trùng ${duplicates}`}
      {skipped > 0 && ` · bỏ qua ${skipped}`}
      {` · lỗi ${errors.length}`}
      {errors.length > 0 && (
        <span className="mt-1 block text-ok/80">
          {errors.slice(0, LIMIT_ERRORS).map(errorLine).join(" · ")}
        </span>
      )}
    </div>
  );
}
