import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GRACE_MS } from "../mic/constants";
import Composer from "./Composer";

const renderComposer = (overrides = {}) => {
  const props = {
    value: "",
    live: "",
    onChange: vi.fn(),
    onSubmit: vi.fn(),
    onToggleListen: vi.fn(),
    ...overrides,
  };
  return { ...props, ...render(<Composer {...props} />) };
};

describe("Composer", () => {
  it("shows the live partial inside the input and locks editing while listening", () => {
    renderComposer({ value: "đã chốt", live: "đang nói", listening: true });

    const textarea = screen.getByLabelText("Câu hỏi");
    expect(textarea).toHaveValue("đã chốt đang nói");
    expect(textarea.readOnly).toBe(true);
  });

  it("ignores the live text and allows typing when the mic is off", () => {
    const { onChange } = renderComposer({
      value: "đã chốt",
      live: "đang nói",
      listening: false,
    });

    const textarea = screen.getByLabelText("Câu hỏi");
    expect(textarea).toHaveValue("đã chốt");

    fireEvent.change(textarea, { target: { value: "đã chốt mới" } });
    expect(onChange).toHaveBeenCalledWith("đã chốt mới");
  });

  it("submits the committed value; the screen appends the spoken tail", () => {
    const { onSubmit } = renderComposer({
      value: "câu đã chốt",
      live: "đang nói",
      listening: true,
    });

    fireEvent.click(screen.getByRole("button", { name: "Hỏi" }));
    expect(onSubmit).toHaveBeenCalledWith("câu đã chốt");
  });

  it("derives the silence hint from GRACE_MS instead of hardcoding seconds", () => {
    renderComposer({ listening: true });
    const label = (GRACE_MS / 1000).toLocaleString("vi-VN");

    expect(
      screen.getByText(new RegExp(`${label} giây im lặng`)),
    ).toBeInTheDocument();
  });
});
