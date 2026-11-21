import { act, fireEvent, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../../services/api";
import { useAnswerReader } from "./useAnswerReader";

const speechMock = {
  start: vi.fn(),
  stop: vi.fn(),
  status: "idle",
};

vi.mock("../../shared/playback/useSpeechPlayer", () => ({
  useSpeechPlayer: () => speechMock,
}));
vi.mock("../../shared/tts/constants", () => ({
  readVoice: () => "giọng",
}));
vi.mock("../../services/api", () => ({
  getAnswerSpeech: vi.fn(),
}));

function Harness() {
  const reader = useAnswerReader();
  return (
    <div>
      <audio ref={reader.audioRef} />
      <button type="button" onClick={() => reader.read({ id: "a1", text: "đáp án một" })}>
        đọc A
      </button>
      <button type="button" onClick={() => reader.read({ id: "a2", text: "đáp án hai" })}>
        đọc B
      </button>
    </div>
  );
}

let playSpy;
let pauseSpy;
let loadSpy;

beforeEach(() => {
  vi.clearAllMocks();
  api.getAnswerSpeech.mockReset();
  speechMock.start.mockReset();
  speechMock.stop.mockReset();
  playSpy = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue(undefined);
  pauseSpy = vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  loadSpy = vi.spyOn(HTMLMediaElement.prototype, "load").mockImplementation(() => {});
});

afterEach(() => {
  playSpy.mockRestore();
  pauseSpy.mockRestore();
  loadSpy.mockRestore();
});

describe("useAnswerReader", () => {
  it("stops a playing cached WAV before starting a stream", async () => {
    api.getAnswerSpeech.mockResolvedValueOnce({ mode: "cached", url: "/wav/1" });
    const view = render(<Harness />);

    fireEvent.click(view.getByText("đọc A"));
    await waitFor(() => expect(playSpy).toHaveBeenCalledTimes(1));

    api.getAnswerSpeech.mockResolvedValueOnce({ mode: "stream" });
    fireEvent.click(view.getByText("đọc B"));

    // The claim silences the element synchronously, before any await.
    expect(pauseSpy).toHaveBeenCalled();
    await waitFor(() =>
      expect(speechMock.start).toHaveBeenCalledWith("đáp án hai", "giọng"),
    );
  });

  it("discards a late cached response from a superseded click", async () => {
    let resolveFirst;
    const first = new Promise((resolve) => {
      resolveFirst = resolve;
    });
    api.getAnswerSpeech
      .mockImplementationOnce(() => first)
      .mockImplementationOnce(() => Promise.resolve({ mode: "stream" }));
    const view = render(<Harness />);

    fireEvent.click(view.getByText("đọc A"));
    await waitFor(() => expect(api.getAnswerSpeech).toHaveBeenCalledTimes(1));
    fireEvent.click(view.getByText("đọc B"));
    await waitFor(() =>
      expect(speechMock.start).toHaveBeenCalledWith("đáp án hai", "giọng"),
    );

    await act(async () => {
      resolveFirst({ mode: "cached", url: "/wav/1" });
    });

    expect(playSpy).not.toHaveBeenCalled();
  });

  it("does not fall back to the stream when cached playback is rejected", async () => {
    playSpy.mockRejectedValue(new Error("NotAllowedError"));
    api.getAnswerSpeech.mockResolvedValueOnce({ mode: "cached", url: "/wav/1" });
    const view = render(<Harness />);

    fireEvent.click(view.getByText("đọc A"));
    await waitFor(() => expect(playSpy).toHaveBeenCalledTimes(1));

    expect(speechMock.start).not.toHaveBeenCalled();
  });
});
