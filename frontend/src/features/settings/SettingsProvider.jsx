// Server-backed settings state plus the local "dirty" staging for fields that
// need an engine reload. One responsibility: settings only.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { useToast } from "../../app/ToastProvider";
import { useLive } from "../dictation/LiveProvider";
import * as api from "../../services/api";

const SettingsContext = createContext(null);

export const useSettings = () => useContext(SettingsContext);

const EMPTY = { values: {}, fields: [], engines: [], warnings: [] };

export function SettingsProvider({ children }) {
  const { notify } = useToast();
  const { snapshot } = useLive();
  const [settings, setSettings] = useState(EMPTY);
  const [dirty, setDirty] = useState({});

  // The live state stream (SSE) already carries the authoritative values; mirror
  // them so a change made from another tab shows up here too.
  useEffect(() => {
    setSettings((previous) => ({
      ...previous,
      values: snapshot.values ?? previous.values,
      warnings: snapshot.warnings ?? previous.warnings,
    }));
  }, [snapshot]);

  const refreshSettings = useCallback(async () => {
    try {
      setSettings(await api.getSettings());
    } catch (error) {
      notify(`Không tải được cài đặt: ${error.message}`);
    }
  }, [notify]);

  useEffect(() => {
    refreshSettings();
  }, [refreshSettings]);

  const applyPatch = useCallback(
    async (change) => {
      try {
        const result = await api.postSettings(change);
        setSettings((previous) => ({
          ...previous,
          values: result.values ?? previous.values,
          fields: result.fields ?? previous.fields,
          engines: result.engines ?? previous.engines,
          warnings: result.warnings ?? previous.warnings,
        }));
        const rejected = result.rejected || {};
        const keys = Object.keys(rejected);
        if (keys.length) {
          notify(`Không hợp lệ: ${keys.map((key) => rejected[key]).join("; ")}`);
          return false;
        }
        return true;
      } catch (error) {
        notify(`Lỗi cài đặt: ${error.message}`);
        return false;
      }
    },
    [notify],
  );

  const setField = useCallback(
    (field, value) => {
      if (field.effect === "live") {
        applyPatch({ [field.key]: value });
      } else {
        setDirty((previous) => ({ ...previous, [field.key]: value }));
      }
    },
    [applyPatch],
  );

  const applyDirty = useCallback(async () => {
    const change = { ...dirty };
    if (!Object.keys(change).length) return;
    if (await applyPatch(change)) {
      setDirty({});
      notify("Đã áp dụng");
    }
  }, [dirty, applyPatch, notify]);

  const resetSettings = useCallback(async () => {
    try {
      const result = await api.resetSettings();
      setSettings((previous) => ({
        ...previous,
        values: result.values ?? previous.values,
        fields: result.fields ?? previous.fields,
        engines: result.engines ?? previous.engines,
        warnings: result.warnings ?? previous.warnings,
      }));
      setDirty({});
      notify("Đã khôi phục mặc định");
    } catch (error) {
      notify(`Lỗi: ${error.message}`);
    }
  }, [notify]);

  const value = useMemo(
    () => ({
      settings,
      dirty,
      refreshSettings,
      applyPatch,
      setField,
      applyDirty,
      resetSettings,
    }),
    [settings, dirty, refreshSettings, applyPatch, setField, applyDirty, resetSettings],
  );

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}
