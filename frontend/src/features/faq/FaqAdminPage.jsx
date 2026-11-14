// Catalogue admin: CRUD, CSV import, reindex, stats and the unanswered worklist.

import { useCallback, useEffect, useRef, useState } from "react";

import AppShell from "../../app/AppShell";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import EmptyState from "../../components/ui/EmptyState";
import * as api from "../../services/api";
import { messageFor } from "../../services/errors";

const EMPTY_FORM = { question: "", answer: "", category: "" };
const SAMPLE_CSV = "question,answer,category\nThủ đô Việt Nam là gì?,Hà Nội.,địa lý\n";

function StatsPanel({ stats, unanswered, audit, onReindex, busy }) {
  return (
    <>
      <section className="mb-4 rounded-xl border border-line bg-white/[0.02] p-3">
        <h2 className="m-0 mb-2 text-[11px] font-semibold tracking-[0.08em] text-faint uppercase">
          Kho câu hỏi
        </h2>
        <dl className="m-0 grid grid-cols-2 gap-y-1.5 text-[12px]">
          <dt className="text-faint">Câu hỏi</dt>
          <dd className="m-0 text-right text-white">{stats.entries ?? 0}</dd>
          <dt className="text-faint">Đang bật</dt>
          <dd className="m-0 text-right text-white">{stats.active ?? 0}</dd>
          <dt className="text-faint">Đã embedding</dt>
          <dd className="m-0 text-right text-white">{stats.embedded ?? 0}</dd>
          <dt className="text-faint">Ngưỡng khớp</dt>
          <dd className="m-0 text-right text-white">
            {stats.threshold != null ? `${Math.round(stats.threshold * 100)}%` : "—"}
          </dd>
          <dt className="text-faint">Model</dt>
          <dd className="m-0 truncate text-right font-mono text-[11px] text-dim">
            {stats.model || "—"}
          </dd>
        </dl>
        {stats.embed_note && (
          <p className="mt-2 mb-0 rounded-lg border border-accent/30 bg-accent/[0.08] px-2 py-1.5 text-[11px] leading-relaxed text-accent">
            {stats.embed_note}
          </p>
        )}
        <Button
          variant="secondary"
          size="sm"
          className="mt-2 w-full"
          onClick={onReindex}
          disabled={busy}
        >
          Embedding lại
        </Button>
      </section>

      <section className="mb-4 rounded-xl border border-line bg-white/[0.02] p-3">
        <h2 className="m-0 mb-2 text-[11px] font-semibold tracking-[0.08em] text-faint uppercase">
          Chưa có đáp án
        </h2>
        {unanswered.length === 0 ? (
          <p className="m-0 text-[12px] text-faint">Chưa có câu nào bị bỏ trống.</p>
        ) : (
          <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
            {unanswered.slice(0, 6).map((item) => (
              <li key={item.question_norm} className="text-[12px] text-dim">
                <span className="text-white">{item.sample || item.question_norm}</span>
                <span className="ml-1 font-mono text-[10.5px] text-faint">
                  ×{item.asks}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-xl border border-line bg-white/[0.02] p-3">
        <h2 className="m-0 mb-2 text-[11px] font-semibold tracking-[0.08em] text-faint uppercase">
          Hoạt động gần đây
        </h2>
        {audit.length === 0 ? (
          <p className="m-0 text-[12px] text-faint">Chưa có thao tác nào.</p>
        ) : (
          <ul className="m-0 flex list-none flex-col gap-1 p-0">
            {audit.slice(0, 6).map((item) => (
              <li key={item.id} className="flex items-baseline gap-1.5 text-[11.5px]">
                <span className="font-mono text-faint">{item.action}</span>
                <span className="truncate text-dim">{item.target || item.detail}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}

export default function FaqAdminPage() {
  const [entries, setEntries] = useState([]);
  const [stats, setStats] = useState({});
  const [unanswered, setUnanswered] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editing, setEditing] = useState("");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [audit, setAudit] = useState([]);
  const [jobs, setJobs] = useState({});
  const timers = useRef({});
  const fileRef = useRef(null);

  useEffect(
    () => () => {
      Object.values(timers.current).forEach((timer) => window.clearInterval(timer));
      timers.current = {};
    },
    [],
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [list, summary, open, recent] = await Promise.all([
        api.getFaqEntries({ q: query }),
        api.getFaqStats(),
        api.getUnanswered(20),
        api.getAudit(10),
      ]);
      setEntries(list.items || []);
      setStats(summary);
      setUnanswered(open.items || []);
      setAudit(recent.items || []);
      setError("");
    } catch (loadError) {
      setError(messageFor(loadError));
    } finally {
      setLoading(false);
    }
  }, [query]);

  useEffect(() => {
    load();
  }, [load]);

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditing("");
  };

  const save = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (editing) {
        await api.updateFaqEntry(editing, form);
      } else {
        await api.createFaqEntry(form);
      }
      resetForm();
      await load();
    } catch (saveError) {
      setError(messageFor(saveError));
    } finally {
      setBusy(false);
    }
  };

  const edit = (entry) => {
    setEditing(entry.id);
    setForm({
      question: entry.question,
      answer: entry.answer,
      category: entry.category || "",
    });
  };

  const remove = async (entry) => {
    if (!window.confirm(`Xoá câu hỏi “${entry.question}”?`)) return;
    setBusy(true);
    try {
      await api.deleteFaqEntry(entry.id);
      if (editing === entry.id) resetForm();
      await load();
    } catch (removeError) {
      setError(messageFor(removeError));
    } finally {
      setBusy(false);
    }
  };

  const toggleActive = async (entry) => {
    setBusy(true);
    try {
      await api.updateFaqEntry(entry.id, { active: !entry.active });
      await load();
    } catch (toggleError) {
      setError(messageFor(toggleError));
    } finally {
      setBusy(false);
    }
  };

  const importFile = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError("");
    setReport(null);
    try {
      const result = await api.importFaqCsv(file);
      setReport(result);
      await load();
    } catch (importError) {
      setError(messageFor(importError));
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const reindex = async () => {
    setBusy(true);
    setError("");
    try {
      await api.reindexFaq();
      await load();
    } catch (reindexError) {
      setError(messageFor(reindexError));
    } finally {
      setBusy(false);
    }
  };

  const prerender = async (entry) => {
    const voice = window.localStorage.getItem("tts.voice") || "";
    setError("");
    try {
      const { job } = await api.prerenderFaq(entry.id, voice);
      setJobs((previous) => ({ ...previous, [entry.id]: job }));
      if (job.status !== "done") {
        const poll = window.setInterval(async () => {
          try {
            const status = await api.getPrerender(job.id);
            setJobs((previous) => ({ ...previous, [entry.id]: status }));
            if (status.status !== "running") {
              window.clearInterval(poll);
              delete timers.current[entry.id];
              load();
            }
          } catch {
            window.clearInterval(poll);
            delete timers.current[entry.id];
          }
        }, 1500);
        timers.current[entry.id] = poll;
      }
    } catch (prerenderError) {
      setError(messageFor(prerenderError));
    }
  };

  return (
    <AppShell
      title="Kho câu hỏi"
      subtitle="Cặp câu hỏi – câu trả lời soạn sẵn, khớp bằng embedding"
      right={
        <StatsPanel stats={stats} unanswered={unanswered} audit={audit}
                    onReindex={reindex} busy={busy} />
      }
      actions={
        <>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            onChange={importFile}
            className="hidden"
            id="faq-import"
          />
          <Button
            variant="secondary"
            size="sm"
            onClick={() => fileRef.current?.click()}
            disabled={busy}
          >
            Nhập CSV
          </Button>
          <Button variant="secondary" size="sm" onClick={load} disabled={loading}>
            Làm mới
          </Button>
        </>
      }
    >
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-5 py-5">
        <div className="mx-auto max-w-[860px] space-y-4">
          {error && (
            <p className="m-0 rounded-lg border border-err/35 bg-err/10 px-3 py-2 text-[12px] text-err">
              {error}
            </p>
          )}

          {report && (
            <div className="rounded-lg border border-ok/30 bg-ok/[0.08] px-3 py-2 text-[12px] text-ok">
              Đã thêm {report.added}/{report.total} câu · trùng {report.duplicates?.length || 0} ·
              lỗi {report.errors?.length || 0}
              {!!report.errors?.length && (
                <span className="mt-1 block text-ok/80">
                  {report.errors.slice(0, 3).map((item) => `dòng ${item.row}: ${item.error}`).join(" · ")}
                </span>
              )}
            </div>
          )}

          <form
            onSubmit={save}
            className="rounded-card border border-line bg-surface-2/60 p-4"
          >
            <div className="mb-2 flex items-center justify-between">
              <h2 className="m-0 text-[13.5px] font-semibold">
                {editing ? "Sửa câu hỏi" : "Thêm câu hỏi"}
              </h2>
              {editing && (
                <Button variant="ghost" size="sm" onClick={resetForm}>
                  Huỷ sửa
                </Button>
              )}
            </div>

            <label className="mb-2 block">
              <span className="mb-1 block text-[12px] text-dim">Câu hỏi</span>
              <input
                value={form.question}
                onChange={(event) => setForm({ ...form, question: event.target.value })}
                placeholder="Thủ đô Việt Nam là gì?"
                className="w-full rounded-control border border-line bg-white/[0.04] px-3 py-2 text-[13px] text-white outline-none placeholder:text-faint focus:border-accent/60"
              />
            </label>

            <label className="mb-2 block">
              <span className="mb-1 block text-[12px] text-dim">Câu trả lời</span>
              <textarea
                value={form.answer}
                onChange={(event) => setForm({ ...form, answer: event.target.value })}
                rows={3}
                placeholder="Câu trả lời nguyên văn sẽ được đọc lên."
                className="w-full resize-y rounded-control border border-line bg-white/[0.04] px-3 py-2 text-[13px] leading-relaxed text-white outline-none placeholder:text-faint focus:border-accent/60"
              />
            </label>

            <div className="flex flex-wrap items-end gap-2">
              <label className="min-w-[180px] flex-1">
                <span className="mb-1 block text-[12px] text-dim">Danh mục</span>
                <input
                  value={form.category}
                  onChange={(event) => setForm({ ...form, category: event.target.value })}
                  placeholder="địa lý, thủ tục, chung…"
                  className="w-full rounded-control border border-line bg-white/[0.04] px-3 py-2 text-[13px] text-white outline-none placeholder:text-faint focus:border-accent/60"
                />
              </label>
              <Button type="submit" variant="primary" disabled={busy}>
                {editing ? "Lưu thay đổi" : "Thêm vào kho"}
              </Button>
            </div>
          </form>

          <div className="flex items-center gap-2">
            <label className="min-w-0 flex-1">
              <span className="sr-only">Tìm trong kho</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Tìm câu hỏi hoặc câu trả lời…"
                className="w-full rounded-control border border-line bg-white/[0.03] px-3 py-2 text-[13px] text-white outline-none placeholder:text-faint focus:border-accent/60"
              />
            </label>
            <span className="text-[11.5px] text-faint">{entries.length} câu</span>
          </div>

          {!loading && !entries.length && (
            <EmptyState
              title="Kho đang trống"
              hint={`Thêm câu hỏi ở trên, hoặc nhập CSV với 3 cột question, answer, category. Mẫu: ${SAMPLE_CSV.split("\n")[1]}`}
            />
          )}

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
                  <div className="flex shrink-0 items-center gap-1.5">
                    {entry.category && <Badge tone="dim">{entry.category}</Badge>}
                    <Badge tone={entry.active ? "ok" : "neutral"}>
                      {entry.active ? "bật" : "tắt"}
                    </Badge>
                  </div>
                </div>
                <div className="mt-2 flex items-center gap-1.5">
                  <Button variant="ghost" size="sm" onClick={() => edit(entry)}>
                    Sửa
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => toggleActive(entry)}
                          disabled={busy}>
                    {entry.active ? "Tắt" : "Bật"}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => prerender(entry)}
                    disabled={busy || jobs[entry.id]?.status === "running"}
                  >
                    {jobs[entry.id]?.status === "running"
                      ? "Đang tạo…"
                      : jobs[entry.id]?.status === "done"
                        ? "Đã lưu bản đọc"
                        : "Tổng hợp sẵn"}
                  </Button>
                  <Button variant="danger" size="sm" onClick={() => remove(entry)}
                          disabled={busy}>
                    Xoá
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </AppShell>
  );
}
