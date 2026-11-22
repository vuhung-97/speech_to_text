// Catalogue admin screen: composition of form, list, stats and question sets.
// State lives in useFaqAdmin/usePrerenderJobs/useFaqDocuments.

import { useRef } from "react";

import AppShell from "../../app/AppShell";
import Alert from "../../components/ui/Alert";
import Button from "../../components/ui/Button";
import { FIELD_CLASS, FIELD_TEXT } from "../../components/ui/fieldStyles";
import FaqDocumentsPanel from "./FaqDocumentsPanel";
import FaqEntryForm from "./FaqEntryForm";
import FaqEntryList from "./FaqEntryList";
import FaqImportReport from "./FaqImportReport";
import FaqStatsPanel from "./FaqStatsPanel";
import { useFaqAdmin } from "./hooks/useFaqAdmin";
import { useFaqDocuments } from "./hooks/useFaqDocuments";
import { usePrerenderJobs } from "./hooks/usePrerenderJobs";

export default function FaqAdminPage() {
  const admin = useFaqAdmin();
  const documents = useFaqDocuments();
  const fileRef = useRef(null);
  const { jobs, prerender } = usePrerenderJobs({
    onFinished: admin.load,
    onError: admin.setError,
  });

  const onImport = async (event) => {
    const file = event.target.files?.[0];
    if (file) await admin.importFile(file);
    documents.load(); // refresh set names/counts after an outline upload
    if (fileRef.current) fileRef.current.value = "";
  };

  const renameDocument = (document) => {
    const name = window.prompt("Tên bộ đề:", document.name);
    if (name && name.trim()) documents.rename(document.id, name.trim());
  };

  const removeDocument = (document) => {
    if (!window.confirm(`Xoá bộ đề “${document.name}” cùng ${document.entry_count} câu?`)) {
      return;
    }
    documents.remove(document.id);
  };

  return (
    <AppShell
      title="Kho câu hỏi"
      right={
        <>
          <FaqStatsPanel
            stats={admin.stats}
            unanswered={admin.unanswered}
            audit={admin.audit}
            onReindex={admin.reindex}
            busy={admin.busy}
          />
          <FaqDocumentsPanel
            documents={documents.documents}
            busy={documents.busy}
            onRename={renameDocument}
            onRemove={removeDocument}
          />
        </>
      }
      actions={
        <>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.docx,text/csv,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
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
            Nhập câu hỏi
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
          {(admin.error || documents.error) && (
            <Alert>{admin.error || documents.error}</Alert>
          )}

          {admin.report && <FaqImportReport report={admin.report} />}

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
                className={`${FIELD_CLASS} w-full rounded-control px-3 py-2 ${FIELD_TEXT}`}
              />
            </label>
            <span className="text-[12px] text-faint">{admin.entries.length} câu</span>
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
