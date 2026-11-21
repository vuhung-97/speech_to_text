import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as api from "../../services/api";
import { useAsk } from "./useAsk";

vi.mock("../../services/api", () => ({
  askQuestion: vi.fn(),
  getSession: vi.fn(),
}));

function answer(overrides = {}) {
  return {
    id: "answer-1",
    turn_id: "turn-1",
    text: "Hà Nội.",
    status: "matched",
    answered: true,
    ...overrides,
  };
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("useAsk", () => {
  it("appends one turn and stores the created session id", async () => {
    api.askQuestion.mockResolvedValue({
      session_id: "session-1",
      question: "Thủ đô?",
      answer: answer(),
    });
    const { result } = renderHook(() => useAsk());

    await act(async () => {
      await result.current.ask("  Thủ đô?  ");
    });

    expect(api.askQuestion).toHaveBeenCalledTimes(1);
    expect(result.current.sessionId).toBe("session-1");
    expect(result.current.turns).toHaveLength(1);
    expect(result.current.turns[0].answer.text).toBe("Hà Nội.");
    expect(result.current.busy).toBe(false);
  });

  it("ignores a second submit while one is in flight", async () => {
    let resolveFirst;
    api.askQuestion.mockImplementation(
      () => new Promise((resolve) => {
        resolveFirst = resolve;
      }),
    );
    const { result } = renderHook(() => useAsk());

    let first;
    let second;
    await act(async () => {
      first = result.current.ask("câu một");
      second = result.current.ask("câu hai");
    });

    expect(api.askQuestion).toHaveBeenCalledTimes(1);
    await expect(second).resolves.toBeNull();

    await act(async () => {
      resolveFirst({ session_id: "s", question: "câu một", answer: answer() });
      await first;
    });
    expect(result.current.turns).toHaveLength(1);
  });

  it("surfaces a transport error and keeps the thread empty", async () => {
    api.askQuestion.mockRejectedValue(new Error("mất kết nối"));
    const { result } = renderHook(() => useAsk());

    await act(async () => {
      await result.current.ask("câu hỏi");
    });

    expect(result.current.error).toBe("mất kết nối");
    expect(result.current.turns).toHaveLength(0);
  });

  it("forwards the selected question set to the API", async () => {
    api.askQuestion.mockResolvedValue({
      session_id: "s",
      question: "câu hỏi",
      answer: answer(),
    });
    const { result } = renderHook(() => useAsk());

    await act(async () => {
      await result.current.ask("câu hỏi", "typed", "doc-9");
    });

    expect(api.askQuestion).toHaveBeenCalledWith(
      "câu hỏi",
      expect.objectContaining({ documentId: "doc-9", source: "typed" }),
    );
  });
});
