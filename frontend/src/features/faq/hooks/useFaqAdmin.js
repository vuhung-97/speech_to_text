// Catalogue admin state: entries, stats, unanswered worklist, audit and the
// active filter. Server access only; the page and its panels are presentational.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import * as api from "../../../services/api";
import { messageFor } from "../../../services/errors";
import { useDebouncedValue } from "../../../utils/useDebouncedValue";
import { useAsyncTask } from "./useAsyncTask";

export const EMPTY_FORM = { question: "", answer: "", category: "" };

export const FILTER_ALL = "all";
export const FILTER_ACTIVE = "active";
export const FILTER_INACTIVE = "inactive";

export const ENTRY_FILTERS = [
  { id: FILTER_ALL, label: "Tất cả" },
  { id: FILTER_ACTIVE, label: "Đang bật" },
  { id: FILTER_INACTIVE, label: "Đang tắt" },
];

const DOCX_EXTENSION = /\.docx$/i;

const isOutlineFile = (name) => DOCX_EXTENSION.test(name || "");

function matchesFilter(entry, filter) {
  if (filter === FILTER_ACTIVE) return entry.active;
  if (filter === FILTER_INACTIVE) return !entry.active;
  return true;
}

export function useFaqAdmin() {
  const [entries, setEntries] = useState([]);
  const [stats, setStats] = useState({});
  const [unanswered, setUnanswered] = useState([]);
  const [audit, setAudit] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editing, setEditing] = useState("");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState(FILTER_ALL);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const { busy, error, setError, run } = useAsyncTask();
  const debouncedQuery = useDebouncedValue(query, 250);
  // A slow response from an older query must never overwrite a newer one.
  const requestRef = useRef(0);

  const load = useCallback(async () => {
    const requestId = requestRef.current + 1;
    requestRef.current = requestId;
    setLoading(true);
    try {
      const [list, summary, open, recent] = await Promise.all([
        api.getFaqEntries({ q: debouncedQuery }),
        api.getFaqStats(),
        api.getUnanswered(20),
        api.getAudit(10),
      ]);
      if (requestId !== requestRef.current) return;
      setEntries(list.items || []);
      setStats(summary);
      setUnanswered(open.items || []);
      setAudit(recent.items || []);
      setError("");
    } catch (loadError) {
      if (requestId !== requestRef.current) return;
      setError(messageFor(loadError));
    } finally {
      if (requestId === requestRef.current) setLoading(false);
    }
  }, [debouncedQuery, setError]);

  useEffect(() => {
    load();
  }, [load]);

  const resetForm = useCallback(() => {
    setForm(EMPTY_FORM);
    setEditing("");
  }, []);

  const save = useCallback(
    async (event) => {
      event.preventDefault();
      const saved = await run(async () => {
        if (editing) {
          await api.updateFaqEntry(editing, form);
        } else {
          await api.createFaqEntry(form);
        }
        resetForm();
        await load();
        return true;
      });
      return saved === true;
    },
    [editing, form, load, resetForm, run],
  );

  const edit = useCallback((entry) => {
    setEditing(entry.id);
    setForm({
      question: entry.question,
      answer: entry.answer,
      category: entry.category || "",
    });
  }, []);

  const remove = useCallback(
    async (entry) => {
      if (!window.confirm(`Xoá câu hỏi “${entry.question}”?`)) return;
      await run(async () => {
        await api.deleteFaqEntry(entry.id);
        if (editing === entry.id) resetForm();
        await load();
      });
    },
    [editing, load, resetForm, run],
  );

  const toggleActive = useCallback(
    async (entry) => {
      await run(async () => {
        await api.updateFaqEntry(entry.id, { active: !entry.active });
        await load();
      });
    },
    [load, run],
  );

  const importFile = useCallback(
    async (file) => {
      if (!file) return;
      setReport(null);
      await run(async () => {
        const result = isOutlineFile(file.name)
          ? await api.importFaqDocx(file)
          : await api.importFaqCsv(file);
        setReport(result);
        await load();
      });
    },
    [load, run],
  );

  const reindex = useCallback(async () => {
    await run(async () => {
      await api.reindexFaq();
      await load();
    });
  }, [load, run]);

  const filteredEntries = useMemo(
    () => entries.filter((entry) => matchesFilter(entry, filter)),
    [entries, filter],
  );
  const isFiltered = Boolean(query.trim()) || filter !== FILTER_ALL;

  return {
    entries,
    filteredEntries,
    stats,
    unanswered,
    audit,
    form,
    setForm,
    editing,
    query,
    setQuery,
    filters: ENTRY_FILTERS,
    filter,
    setFilter,
    isFiltered,
    busy,
    error,
    setError,
    report,
    loading,
    load,
    save,
    edit,
    resetForm,
    remove,
    toggleActive,
    importFile,
    reindex,
  };
}
