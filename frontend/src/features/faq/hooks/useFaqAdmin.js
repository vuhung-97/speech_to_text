// Catalogue admin state: entries, stats, unanswered worklist and audit.
// Server access only; the page and its panels are presentational.

import { useCallback, useEffect, useState } from "react";

import * as api from "../../../services/api";
import { messageFor } from "../../../services/errors";

export const EMPTY_FORM = { question: "", answer: "", category: "" };

export function useFaqAdmin() {
  const [entries, setEntries] = useState([]);
  const [stats, setStats] = useState({});
  const [unanswered, setUnanswered] = useState([]);
  const [audit, setAudit] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editing, setEditing] = useState("");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

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

  const resetForm = useCallback(() => {
    setForm(EMPTY_FORM);
    setEditing("");
  }, []);

  const save = useCallback(
    async (event) => {
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
    },
    [editing, form, load, resetForm],
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
    },
    [editing, load, resetForm],
  );

  const toggleActive = useCallback(
    async (entry) => {
      setBusy(true);
      try {
        await api.updateFaqEntry(entry.id, { active: !entry.active });
        await load();
      } catch (toggleError) {
        setError(messageFor(toggleError));
      } finally {
        setBusy(false);
      }
    },
    [load],
  );

  const importFile = useCallback(
    async (file) => {
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
      }
    },
    [load],
  );

  const reindex = useCallback(async () => {
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
  }, [load]);

  return {
    entries,
    stats,
    unanswered,
    audit,
    form,
    setForm,
    editing,
    query,
    setQuery,
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
