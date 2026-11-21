import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as api from "../../../services/api";
import { usePrerenderJobs } from "./usePrerenderJobs";

vi.mock("../../../services/api", () => ({
  prerenderFaq: vi.fn(),
  getPrerender: vi.fn(),
}));

afterEach(() => {
  vi.clearAllMocks();
});

describe("usePrerenderJobs", () => {
  it("polls a running job once and refreshes when it settles", async () => {
    api.prerenderFaq.mockResolvedValue({
      job: { id: "job-1", status: "running" },
    });
    api.getPrerender.mockResolvedValue({ id: "job-1", status: "done" });
    const onFinished = vi.fn();
    const { result } = renderHook(() => usePrerenderJobs({ onFinished }));

    await act(async () => {
      await result.current.prerender({ id: "entry-1" });
    });
    expect(result.current.jobs["entry-1"].status).toBe("running");

    await waitFor(
      () => {
        expect(onFinished).toHaveBeenCalledTimes(1);
        expect(result.current.jobs["entry-1"].status).toBe("done");
      },
      { timeout: 4_000 },
    );
  });

  it("records an already cached job without polling", async () => {
    api.prerenderFaq.mockResolvedValue({
      job: { id: "job-2", status: "done", seconds: 1.2 },
    });
    const onFinished = vi.fn();
    const { result } = renderHook(() => usePrerenderJobs({ onFinished }));

    await act(async () => {
      await result.current.prerender({ id: "entry-2" });
    });

    expect(api.getPrerender).not.toHaveBeenCalled();
    expect(onFinished).not.toHaveBeenCalled();
    expect(result.current.jobs["entry-2"].seconds).toBe(1.2);
  });

  it("reports a failed start through onError", async () => {
    api.prerenderFaq.mockRejectedValue(new Error("đang bận"));
    const onError = vi.fn();
    const { result } = renderHook(() => usePrerenderJobs({ onError }));

    await act(async () => {
      await result.current.prerender({ id: "entry-3" });
    });

    expect(onError).toHaveBeenCalledWith("đang bận");
  });
});
