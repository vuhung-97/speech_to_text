// Question-set state for the admin panel and the Q&A filter picker.
// Server state only; panels render it.

import { useCallback, useEffect, useState } from "react";

import * as api from "../../../services/api";
import { messageFor } from "../../../services/errors";

export const DOCUMENT_FILTER_KEY = "qa.document";

export function useFaqDocuments() {
  const [documents, setDocuments] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

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
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const rename = useCallback(
    async (documentId, name) => {
      setBusy(true);
      setError("");
      try {
        await api.renameFaqDocument(documentId, name);
        await load();
      } catch (renameError) {
        setError(messageFor(renameError));
      } finally {
        setBusy(false);
      }
    },
    [load],
  );

  const remove = useCallback(
    async (documentId) => {
      setBusy(true);
      setError("");
      try {
        await api.deleteFaqDocument(documentId);
        await load();
      } catch (removeError) {
        setError(messageFor(removeError));
      } finally {
        setBusy(false);
      }
    },
    [load],
  );

  return { documents, busy, error, load, rename, remove };
}
