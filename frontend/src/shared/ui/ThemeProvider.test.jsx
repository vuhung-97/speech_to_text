import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { ThemeProvider, useTheme } from "./ThemeProvider";

function Harness() {
  const { theme, toggle, setTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <button type="button" onClick={toggle}>
        toggle
      </button>
      <button type="button" onClick={() => setTheme("light")}>
        light
      </button>
      <button type="button" onClick={() => setTheme("dark")}>
        dark
      </button>
    </div>
  );
}

function renderTheme() {
  return render(
    <ThemeProvider>
      <Harness />
    </ThemeProvider>,
  );
}

beforeEach(() => {
  window.localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  document.documentElement.style.colorScheme = "";
});

afterEach(cleanup);

describe("ThemeProvider", () => {
  it("defaults to dark and persists an explicit choice", () => {
    renderTheme();

    expect(screen.getByTestId("theme")).toHaveTextContent("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(document.documentElement.style.colorScheme).toBe("dark");

    fireEvent.click(screen.getByRole("button", { name: "toggle" }));

    expect(screen.getByTestId("theme")).toHaveTextContent("light");
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(window.localStorage.getItem("stt.theme")).toBe("light");
  });

  it("reads the saved theme on mount", () => {
    window.localStorage.setItem("stt.theme", "light");
    renderTheme();

    expect(screen.getByTestId("theme")).toHaveTextContent("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("ignores an invalid saved value", () => {
    window.localStorage.setItem("stt.theme", "neon");
    renderTheme();

    expect(screen.getByTestId("theme")).toHaveTextContent("dark");
  });

  it("updates the browser theme-color metadata", () => {
    const meta = document.createElement("meta");
    meta.name = "theme-color";
    meta.content = "#08090b";
    document.head.append(meta);
    renderTheme();

    act(() => {
      fireEvent.click(screen.getByRole("button", { name: "light" }));
    });

    expect(meta.content).toBe("#f3f0e8");
    meta.remove();
  });
});
