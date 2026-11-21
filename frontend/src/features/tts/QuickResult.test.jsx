import { cleanup, fireEvent, render } from "@testing-library/react";
import { useRef } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { beginPlayback, stopAllPlayback } from "../../shared/playback/playbackChannel";
import QuickResult from "./QuickResult";

function Harness({ audio = { url: "blob:x", seconds: 1 } }) {
  const audioRef = useRef(null);
  return <QuickResult audio={audio} audioRef={audioRef} />;
}

let playSpy;
let pauseSpy;
let loadSpy;

beforeEach(() => {
  playSpy = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue(undefined);
  pauseSpy = vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  loadSpy = vi.spyOn(HTMLMediaElement.prototype, "load").mockImplementation(() => {});
  // Release a claim left over from the previous test with the spies in place.
  stopAllPlayback();
});

afterEach(() => {
  cleanup();
  stopAllPlayback();
  playSpy.mockRestore();
  pauseSpy.mockRestore();
  loadSpy.mockRestore();
});

describe("QuickResult", () => {
  it("renders the finished WAV without crashing", () => {
    const view = render(<Harness />);
    expect(view.container.querySelector("audio")).not.toBeNull();
    expect(playSpy).toHaveBeenCalled();
  });

  it("pauses the element when it unmounts", () => {
    const view = render(<Harness />);
    pauseSpy.mockClear();

    view.unmount();

    expect(pauseSpy).toHaveBeenCalled();
  });

  it("claims the channel again when the user presses play manually", () => {
    const otherStop = vi.fn();
    const view = render(<Harness />);

    // Another source takes over (this pauses the quick WAV).
    beginPlayback(otherStop);
    const audio = view.container.querySelector("audio");
    fireEvent.play(audio);

    expect(otherStop).toHaveBeenCalled();
  });
});
