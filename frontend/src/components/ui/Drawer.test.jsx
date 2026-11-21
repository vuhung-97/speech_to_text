import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import Drawer from "./Drawer";

function panel(props = {}) {
  return (
    <Drawer open onClose={vi.fn()} label="Kiểm thử" title="Kiểm thử" {...props}>
      <button type="button">Bên trong</button>
    </Drawer>
  );
}

describe("Drawer", () => {
  it("closes on Escape", () => {
    const onClose = vi.fn();
    render(panel({ onClose }));

    fireEvent.keyDown(document, { key: "Escape" });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("returns focus to the trigger when it closes", () => {
    const trigger = document.createElement("button");
    document.body.append(trigger);
    trigger.focus();

    const view = render(panel());
    view.rerender(
      <Drawer open={false} onClose={() => {}} label="Kiểm thử" title="Kiểm thử">
        <button type="button">Bên trong</button>
      </Drawer>,
    );

    expect(document.activeElement).toBe(trigger);
    trigger.remove();
  });

  it("does not listen for Escape while closed", () => {
    const onClose = vi.fn();
    render(panel({ open: false, onClose }));

    fireEvent.keyDown(document, { key: "Escape" });

    expect(onClose).not.toHaveBeenCalled();
  });
});
