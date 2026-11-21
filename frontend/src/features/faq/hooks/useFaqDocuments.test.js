import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../../../services/api";
import { DOCUMENT_FILTER_KEY, useFaqDocuments } from "./useFaqDocuments";

vi.mock("../../../services/api", () => ({
  getFaqDocuments: vi.fn(),
  renameFaqDocument: vi.fn(),
  deleteFaqDocument: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks();
  api.getFaqDocuments.mockResolvedValue({
    items: [
      { id: "d1", name: "de_a.docx", entry_count: 2 },
      { id: "d2", name: "de_b.docx", entry_count: 5 },
    ],
  });
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("useFaqDocuments", () => {
  it("loads the question sets on mount", async () => {
    const { result } = renderHook(() => useFaqDocuments());

    await waitFor(() => expect(result.current.documents).toHaveLength(2));
    expect(result.current.error).toBe("");
  });

  it("renames a set and reloads the list", async () => {
    api.renameFaqDocument.mockResolvedValue({ ok: true });
    const { result } = renderHook(() => useFaqDocuments());
    await waitFor(() => expect(result.current.documents).toHaveLength(2));

    await act(async () => {
      await result.current.rename("d1", "Đề A");
    });

    expect(api.renameFaqDocument).toHaveBeenCalledWith("d1", "Đề A");
    expect(api.getFaqDocuments).toHaveBeenCalledTimes(2);
  });

  it("removes a set and reloads the list", async () => {
    api.deleteFaqDocument.mockResolvedValue({ ok: true });
    const { result } = renderHook(() => useFaqDocuments());
    await waitFor(() => expect(result.current.documents).toHaveLength(2));

    await act(async () => {
      await result.current.remove("d2");
    });

    expect(api.deleteFaqDocument).toHaveBeenCalledWith("d2");
    expect(api.getFaqDocuments).toHaveBeenCalledTimes(2);
  });

  it("exposes a single storage key for the Q&A filter", () => {
    expect(DOCUMENT_FILTER_KEY).toBe("qa.document");
  });
});
