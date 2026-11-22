// Question-set state for the admin panel and the Q&A filter picker.
// Server state only; panels render it.

import { useCallback, useEffect, useState } from "react";

import * as api from "../../../services/api";
import { messageFor } from "../../../services/errors";
import { useAsyncTask } from "./useAsyncTask";

export const DOCUMENT_FILTER_KEY = "qa.document";

function readSelected() {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(DOCUMENT_FILTER_KEY) || "";
}

export function useFaqDocuments() {
  const [documents, setDocuments] = useState([]);
  const [selectedId, setSelectedId] = useState(readSelected);
  const { busy, error, setError, setBusy, run } = useAsyncTask();

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const data = await api.getFaqDocuments();
      setDocuments(data.items || []);
      setError("");
    } catch (loadError) {
      setError(messageFor(loadError));
    } finally {
      setBusy(false);
    }
  }, [setBusy, setError]);

  useEffect(() => {
    load();
  }, [load]);

  // The Q&A filter is the same concept here: one owner for the key, the state
  // and the "forget it once deleted" rule.
  const select = useCallback((documentId) => {
    const value = documentId || "";
    setSelectedId(value);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(DOCUMENT_FILTER_KEY, value);
    }
  }, []);

  useEffect(() => {
    if (!selectedId || !documents.length) return;
    if (documents.some((item) => item.id === selectedId)) return;
    select("");
  }, [documents, selectedId, select]);

  const rename = useCallback(
    async (documentId, name) => {
      await run(async () => {
        await api.renameFaqDocument(documentId, name);
        await load();
      });
    },
    [load, run],
  );

  const remove = useCallback(
    async (documentId) => {
      await run(async () => {
        await api.deleteFaqDocument(documentId);
        await load();
      });
    },
    [load, run],
  );

  return {
    documents,
    selectedId,
    select,
    busy,
    error,
    load,
    rename,
    remove,
  };
}
