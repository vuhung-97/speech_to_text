import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../../services/api";
import { VoiceProvider } from "../../shared/tts/VoiceProvider";
import VoiceSettings from "./VoiceSettings";

const speech = vi.hoisted(() => ({
  busy: false,
  error: "",
  start: vi.fn(),
  stop: vi.fn(),
}));

vi.mock("../../services/api", () => ({
  getTtsVoices: vi.fn(),
  preloadTts: vi.fn(),
  getTtsStatus: vi.fn(),
}));

vi.mock("../../shared/playback/useSpeechPlayer", () => ({
  useSpeechPlayer: () => speech,
}));

function renderSettings() {
  return render(
    <VoiceProvider>
      <VoiceSettings />
    </VoiceProvider>,
  );
}

beforeEach(() => {
  window.localStorage.clear();
  speech.start.mockClear();
  speech.stop.mockClear();
  api.preloadTts.mockResolvedValue({ ok: true, preloading: true });
  api.getTtsStatus.mockResolvedValue({ preloading: false, loaded: true });
  api.getTtsVoices.mockResolvedValue({
    voices: [
      { id: "giọng-a", label: "Giọng A" },
      { id: "giọng-b", label: "Giọng B" },
    ],
    default: "giọng-a",
    available: true,
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("VoiceSettings", () => {
  it("shows the catalog and preloads a newly chosen voice", async () => {
    renderSettings();

    const select = await screen.findByLabelText("Giọng đọc");
    await waitFor(() =>
      expect(screen.getByRole("option", { name: "Giọng B" })).toBeInTheDocument(),
    );

    await act(async () => {
      fireEvent.change(select, { target: { value: "giọng-b" } });
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(window.localStorage.getItem("tts.voice")).toBe("giọng-b");
    expect(api.preloadTts).toHaveBeenCalledWith("giọng-b");
  });

  it("reads the sample text with the selected voice", async () => {
    renderSettings();

    await waitFor(() =>
      expect(screen.getByRole("option", { name: "Giọng A" })).toBeInTheDocument(),
    );
    const details = screen.getByText("Thử giọng").closest("details");
    details.open = true;
    const sample = screen.getByLabelText("Nội dung thử");
    fireEvent.change(sample, { target: { value: "Đọc thử tiếng Việt." } });
    fireEvent.click(screen.getByRole("button", { name: "Test giọng" }));

    expect(speech.start).toHaveBeenCalledWith("Đọc thử tiếng Việt.", "giọng-a", 1);
  });

  it("does not surface a 405 from an older server without preload", async () => {
    api.preloadTts.mockRejectedValue(
      Object.assign(new Error("HTTP 405"), { status: 405 }),
    );
    renderSettings();

    const select = await screen.findByLabelText("Giọng đọc");
    await waitFor(() =>
      expect(screen.getByRole("option", { name: "Giọng B" })).toBeInTheDocument(),
    );
    await act(async () => {
      fireEvent.change(select, { target: { value: "giọng-b" } });
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(screen.queryByText("HTTP 405")).not.toBeInTheDocument();
  });

  it("persists the reading speed and applies it on the next play", async () => {
    renderSettings();

    await waitFor(() =>
      expect(screen.getByRole("option", { name: "Giọng A" })).toBeInTheDocument(),
    );
    const details = screen.getByText("Thử giọng").closest("details");
    details.open = true;
    const slider = screen.getByLabelText("Tốc độ đọc");
    fireEvent.change(slider, { target: { value: "1.4" } });
    fireEvent.click(screen.getByRole("button", { name: "Test giọng" }));

    expect(window.localStorage.getItem("tts.speed")).toBe("1.4");
    expect(speech.start).toHaveBeenCalledWith(
      "Xin chào, đây là giọng đọc thử nghiệm.",
      "giọng-a",
      1.4,
    );
  });

  it("shows the unavailable reason and a retry action", async () => {
    api.getTtsVoices.mockResolvedValue({
      voices: [],
      available: false,
      reason: "chưa cài package 'vieneu'",
    });

    renderSettings();

    expect(await screen.findByText("chưa cài package 'vieneu'")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Thử lại" })).toBeInTheDocument();
  });
});
