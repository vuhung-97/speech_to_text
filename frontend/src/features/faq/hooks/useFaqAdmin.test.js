import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../../../services/api";
import { useFaqAdmin } from "./useFaqAdmin";

vi.mock("../../../services/api", () => ({
  getFaqEntries: vi.fn(),
  getFaqStats: vi.fn(),
  getUnanswered: vi.fn(),
  getAudit: vi.fn(),
  importFaqCsv: vi.fn(),
  importFaqDocx: vi.fn(),
  createFaqEntry: vi.fn(),
  updateFaqEntry: vi.fn(),
  deleteFaqEntry: vi.fn(),
  reindexFaq: vi.fn(),
}));

const file = (name) => new File(["noi dung"], name);

async function mounted() {
  const view = renderHook(() => useFaqAdmin());
  // Let the initial catalogue fetch settle before exercising an import.
  await waitFor(() => expect(api.getFaqEntries).toHaveBeenCalled());
  return view;
}

beforeEach(() => {
  api.getFaqEntries.mockResolvedValue({ items: [] });
  api.getFaqStats.mockResolvedValue({});
  api.getUnanswered.mockResolvedValue({ items: [] });
  api.getAudit.mockResolvedValue({ items: [] });
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("useFaqAdmin import routing", () => {
  it("sends a .docx outline to the docx endpoint", async () => {
    api.importFaqDocx.mockResolvedValue({
      total: 2,
      added: 2,
      updated: 0,
      skipped: 0,
      errors: [],
    });
    const { result } = await mounted();

    await act(async () => {
      await result.current.importFile(file("de_cuong.DOCX"));
    });

    expect(api.importFaqDocx).toHaveBeenCalledTimes(1);
    expect(api.importFaqCsv).not.toHaveBeenCalled();
    expect(result.current.report.added).toBe(2);
  });

  it("keeps CSV uploads on the CSV endpoint", async () => {
    api.importFaqCsv.mockResolvedValue({
      total: 1,
      added: 1,
      duplicates: [],
      errors: [],
    });
    const { result } = await mounted();

    await act(async () => {
      await result.current.importFile(file("faq.csv"));
    });

    expect(api.importFaqCsv).toHaveBeenCalledTimes(1);
    expect(api.importFaqDocx).not.toHaveBeenCalled();
    expect(result.current.report.added).toBe(1);
  });

  it("surfaces a failed import as an error message", async () => {
    api.importFaqDocx.mockRejectedValue(new Error("tệp hỏng"));
    const { result } = await mounted();

    await act(async () => {
      await result.current.importFile(file("hỏng.docx"));
    });

    expect(result.current.report).toBeNull();
    expect(result.current.error).toContain("tệp hỏng");
  });
});
