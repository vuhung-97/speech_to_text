// One busy/error envelope for every catalogue mutation.
//
// Callers pass the action; this hook owns the in-flight flag, the error text and
// the rule that a failure becomes a user message. A slow action cannot leave
// `busy` stuck because the flag is cleared in `finally`.

import { useCallback, useState } from "react";

import { messageFor } from "../../../services/errors";

export function useAsyncTask() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const run = useCallback(async (action, { clearError = true } = {}) => {
    setBusy(true);
    if (clearError) setError("");
    try {
      return await action();
    } catch (actionError) {
      setError(messageFor(actionError));
      return undefined;
    } finally {
      setBusy(false);
    }
  }, []);

  return { busy, error, setError, setBusy, run };
}
