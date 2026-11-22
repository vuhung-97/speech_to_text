import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AnswerCard from "./AnswerCard";

const ANSWER = {
  id: "a1",
  text: "Đây là nội dung câu trả lời.",
  status: "matched",
  matched: null,
  candidates: [],
};

afterEach(cleanup);

describe("AnswerCard reading controls", () => {
  it("turns the read button into progress + elapsed/total while playing", () => {
    render(
      <AnswerCard
        answer={ANSWER}
        playing
        progress={0.2}
        seconds={4}
        estimated={21}
        onStop={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("button", { name: /Đang đọc/ }),
    ).toBeInTheDocument();
    expect(screen.getByText("4s/21s")).toBeInTheDocument();
  });

  it("stops on a second press and returns to the read button", () => {
    const onStop = vi.fn();
    const { rerender } = render(
      <AnswerCard
        answer={ANSWER}
        playing
        progress={0.2}
        seconds={4}
        estimated={21}
        onStop={onStop}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Đang đọc/ }));
    expect(onStop).toHaveBeenCalledTimes(1);

    rerender(
      <AnswerCard
        answer={ANSWER}
        playing={false}
        onRead={vi.fn()}
        onStop={onStop}
      />,
    );
    expect(screen.getByRole("button", { name: "Đọc" })).toBeInTheDocument();
    expect(screen.queryByText("4s/21s")).not.toBeInTheDocument();
  });
});
