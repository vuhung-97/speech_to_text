// Catalogue admin screen: composition of form, list and stats panels.
// State lives in useFaqAdmin/usePrerenderJobs.

import { useRef } from "react";

import AppShell from "../../app/AppShell";
import Button from "../../components/ui/Button";
import FaqEntryForm from "./FaqEntryForm";
import FaqEntryList from "./FaqEntryList";
import FaqStatsPanel from "./FaqStatsPanel";
import { useFaqAdmin } from "./hooks/useFaqAdmin";
import { usePrerenderJobs } from "./hooks/usePrerenderJobs";

export default function FaqAdminPage() {
  const admin = useFaqAdmin();
  const fileRef = useRef(null);
  const { jobs, prerender } = usePrerenderJobs({
    onFinished: admin.load,
    onError: admin.setError,
  });

  const onImport = async (event) => {
    const file = event.target.files?.[0];
    if (file) await admin.importFile(file);
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <AppShell
      title="Kho câu hỏi"
      subtitle="Cặp câu hỏi – câu trả lời soạn sẵn, khớp bằng embedding"
      right={
        <FaqStatsPanel
          stats={admin.stats}
          unanswered={admin.unanswered}
          audit={admin.audit}
          onReindex={admin.reindex}
          busy={admin.busy}
        />
      }
      actions={
        <>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            onChange={onImport}
            className="hidden"
            id="faq-import"
          />
          <Button
            variant="secondary"
            size="sm"
            onClick={() => fileRef.current?.click()}
            disabled={admin.busy}
          >
            Nhập CSV
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={admin.load}
            disabled={admin.loading}
          >
            Làm mới
          </Button>
        </>
      }
    >
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-5 py-5">
        <div className="mx-auto max-w-[860px] space-y-4">
          {admin.error && (
            <p className="m-0 rounded-lg border border-err/35 bg-err/10 px-3 py-2 text-[12px] text-err">
              {admin.error}
            </p>
          )}

          {admin.report && (
            <div className="rounded-lg border border-ok/30 bg-ok/[0.08] px-3 py-2 text-[12px] text-ok">
              Đã thêm {admin.report.added}/{admin.report.total} câu · trùng{" "}
              {admin.report.duplicates?.length || 0} · lỗi{" "}
              {admin.report.errors?.length || 0}
              {!!admin.report.errors?.length && (
                <span className="mt-1 block text-ok/80">
                  {admin.report.errors
                    .slice(0, 3)
                    .map((item) => `dòng ${item.row}: ${item.error}`)
                    .join(" · ")}
                </span>
              )}
            </div>
          )}

          <FaqEntryForm
            form={admin.form}
            editing={admin.editing}
            busy={admin.busy}
            onChange={(patch) => admin.setForm((previous) => ({ ...previous, ...patch }))}
            onSubmit={admin.save}
            onCancel={admin.resetForm}
          />

          <div className="flex items-center gap-2">
            <label className="min-w-0 flex-1">
              <span className="sr-only">Tìm trong kho</span>
              <input
                value={admin.query}
                onChange={(event) => admin.setQuery(event.target.value)}
                placeholder="Tìm câu hỏi hoặc câu trả lời…"
                className="w-full rounded-control border border-line bg-white/[0.03] px-3 py-2 text-[13px] text-white outline-none placeholder:text-faint focus:border-accent/60"
              />
            </label>
            <span className="text-[11.5px] text-faint">{admin.entries.length} câu</span>
          </div>

          <FaqEntryList
            entries={admin.entries}
            jobs={jobs}
            busy={admin.busy}
            loading={admin.loading}
            onEdit={admin.edit}
            onToggle={admin.toggleActive}
            onPrerender={prerender}
            onRemove={admin.remove}
          />
        </div>
      </div>
    </AppShell>
  );
}
