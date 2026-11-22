// Catalogue admin screen: composition of stats, filters, list and editor.
// State lives in useFaqAdmin/usePrerenderJobs/useFaqDocuments.

import { useRef, useState } from "react";

import AppShell from "../../app/AppShell";
import Alert from "../../components/ui/Alert";
import Button from "../../components/ui/Button";
import Drawer from "../../components/ui/Drawer";
import SearchInput from "../../components/ui/SearchInput";
import FaqDocumentsPanel from "./FaqDocumentsPanel";
import FaqEntryForm from "./FaqEntryForm";
import FaqEntryList from "./FaqEntryList";
import FaqImportReport from "./FaqImportReport";
import FaqStatsPanel from "./FaqStatsPanel";
import { useFaqAdmin } from "./hooks/useFaqAdmin";
import { useFaqDocuments } from "./hooks/useFaqDocuments";
import { usePrerenderJobs } from "./hooks/usePrerenderJobs";

function Stat({ value, label }) {
  return (
    <div className="rounded-xl border border-line bg-wash p-3">
      <b className="block text-[18px] font-semibold tracking-[-0.03em] text-content">
        {value}
      </b>
      <span className="mt-0.5 block text-[10px] text-faint">{label}</span>
    </div>
  );
}

export default function FaqAdminPage() {
  const admin = useFaqAdmin();
  const documents = useFaqDocuments();
  const fileRef = useRef(null);
  const [formOpen, setFormOpen] = useState(false);

  const { jobs, prerender } = usePrerenderJobs({
    onFinished: admin.load,
    onError: admin.setError,
  });

  const openNew = () => {
    admin.resetForm();
    setFormOpen(true);
  };

  const openEdit = (entry) => {
    admin.edit(entry);
    setFormOpen(true);
  };

  const closeForm = () => {
    setFormOpen(false);
    admin.resetForm();
  };

  const submitForm = async (event) => {
    event.preventDefault();
    const saved = await admin.save(event);
    if (saved) setFormOpen(false);
  };

  const onImport = async (event) => {
    const file = event.target.files?.[0];
    if (file) await admin.importFile(file);
    documents.load();
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
      subtitle={`${admin.stats.entries ?? 0} câu · ${documents.documents.length} bộ đề`}
      rightTitle="Tổng quan"
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
    >
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-[900px]">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="m-0 text-[22px] font-semibold tracking-[-0.035em] sm:text-[23px]">
                Kho câu hỏi
              </h2>
              <p className="m-0 mt-1 text-[11.5px] text-faint">
                {admin.stats.entries ?? 0} câu · {admin.stats.active ?? 0} đang bật ·{" "}
                {documents.documents.length} bộ đề
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
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
                Nhập tệp
              </Button>
              <Button variant="primary" size="sm" onClick={openNew}>
                Thêm câu hỏi
              </Button>
            </div>
          </div>

          <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Stat value={admin.stats.entries ?? 0} label="Câu hỏi" />
            <Stat value={admin.stats.active ?? 0} label="Đang bật" />
            <Stat value={admin.stats.embedded ?? 0} label="Đã embedding" />
            <Stat
              value={
                admin.stats.threshold != null
                  ? `${Math.round(admin.stats.threshold * 100)}%`
                  : "—"
              }
              label="Ngưỡng khớp"
            />
          </div>

          {(admin.error || documents.error) && (
            <Alert className="mb-3">{admin.error || documents.error}</Alert>
          )}

          {admin.report && (
            <div className="mb-3">
              <FaqImportReport report={admin.report} />
            </div>
          )}

          <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
            <SearchInput
              label="Tìm trong kho"
              value={admin.query}
              onChange={(event) => admin.setQuery(event.target.value)}
              placeholder="Tìm câu hỏi hoặc câu trả lời…"
              className="w-full sm:w-auto sm:min-w-[240px] sm:flex-1"
            />

            <div className="flex flex-wrap items-center gap-2">
              {admin.filters.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => admin.setFilter(item.id)}
                  aria-pressed={admin.filter === item.id}
                  className={`min-h-11 rounded-full border px-3 py-1 text-[10.5px] transition focus-ring sm:min-h-8 ${
                    admin.filter === item.id
                      ? "border-accent/30 bg-accent/10 text-accent"
                      : "border-line text-faint hover:bg-wash-hover hover:text-content"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          <FaqEntryList
            entries={admin.filteredEntries}
            jobs={jobs}
            busy={admin.busy}
            loading={admin.loading}
            onEdit={openEdit}
            onToggle={admin.toggleActive}
            onPrerender={prerender}
            onRemove={admin.remove}
            emptyTitle={
              admin.isFiltered ? "Không tìm thấy câu hỏi" : "Kho đang trống"
            }
            emptyHint={
              admin.isFiltered
                ? "Thử từ khoá khác hoặc chọn bộ lọc khác."
                : "Thêm câu hỏi hoặc nhập tệp .docx/CSV."
            }
          />
        </div>
      </div>

      <Drawer
        open={formOpen}
        onClose={closeForm}
        label={admin.editing ? "Sửa câu hỏi" : "Thêm câu hỏi"}
        title={admin.editing ? "Sửa câu hỏi" : "Thêm câu hỏi"}
        subtitle="Câu trả lời sẽ được đọc nguyên văn từ kho."
        width="w-[min(500px,100vw)]"
      >
        {admin.error && <Alert className="mb-3">{admin.error}</Alert>}
        <FaqEntryForm
          form={admin.form}
          editing={admin.editing}
          busy={admin.busy}
          onChange={(patch) => admin.setForm((previous) => ({ ...previous, ...patch }))}
          onSubmit={submitForm}
          onCancel={closeForm}
          inDrawer
        />
      </Drawer>
    </AppShell>
  );
}
