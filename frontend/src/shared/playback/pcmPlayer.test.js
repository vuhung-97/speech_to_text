import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PcmPlayer } from "./pcmPlayer";

let sources = [];
let originalContext;

class FakeSource {
  constructor(context) {
    this.context = context;
    this.startAt = null;
    this.onended = null;
    this.playbackRate = { value: 1 };
  }

  connect() {}

  start(at) {
    this.startAt = at;
  }

  stop() {
    this.onended?.();
  }
}

class FakeContext {
  constructor() {
    this.currentTime = 0;
    this.destination = {};
    this.state = "running";
    sources = [];
  }

  createGain() {
    return { gain: { value: 1 }, connect() {} };
  }

  createBuffer(_channels, length, rate) {
    return { duration: length / rate, copyToChannel() {} };
  }

  createBufferSource() {
    const source = new FakeSource(this);
    sources.push(source);
    return source;
  }

  async resume() {}

  async close() {}
}

const block = (seconds = 0.1, rate = 1000) =>
  new Float32Array(Math.round(seconds * rate));

beforeEach(() => {
  originalContext = window.AudioContext;
  window.AudioContext = FakeContext;
});

afterEach(() => {
  window.AudioContext = originalContext;
});

describe("PcmPlayer scheduling", () => {
  it("never schedules two blocks on top of each other", () => {
    const player = new PcmPlayer({ prebuffer: 0 });
    player.setSampleRate(1000);

    for (let index = 0; index < 60; index += 1) player.push(block());

    expect(sources.length).toBeGreaterThan(30);
    for (let index = 1; index < sources.length; index += 1) {
      expect(sources[index].startAt).toBeGreaterThanOrEqual(
        sources[index - 1].startAt + 0.1 - 1e-9,
      );
    }
    // 6 s received, only ~4 s scheduled ahead; the rest waits in the queue.
    expect(player.bufferedSeconds).toBeGreaterThan(5.5);
    player.stop();
  });

  it("scales scheduled duration by the requested playback speed", () => {
    const player = new PcmPlayer({ prebuffer: 0, speed: 2 });
    player.setSampleRate(1000);

    for (let index = 0; index < 3; index += 1) player.push(block());

    expect(sources[0].playbackRate.value).toBe(2);
    expect(sources[1].startAt).toBeCloseTo(sources[0].startAt + 0.05, 6);
    expect(player.bufferedSeconds).toBeCloseTo(0.15, 6);
    player.stop();
  });

  it("schedules only within the configured lookahead", () => {
    const player = new PcmPlayer({ prebuffer: 0.2, lookahead: 2 });
    player.setSampleRate(1000);

    for (let index = 0; index < 60; index += 1) player.push(block());

    const first = sources[0].startAt;
    const last = sources[sources.length - 1].startAt;
    expect(last - first).toBeLessThan(2.1);
    player.stop();
  });

  it("pauses the producer above high water and resumes after draining", async () => {
    const player = new PcmPlayer({ prebuffer: 0 });
    player.setSampleRate(1000);

    for (let index = 0; index < 70; index += 1) player.push(block());

    let resumed = false;
    const blocked = player.push(block()).then(() => {
      resumed = true;
    });
    expect(resumed).toBe(false);

    // Play everything out: advance the clock to each source's end, let the
    // scheduler pump the next block, until the buffer falls under low water.
    let now = 0;
    while (sources.length) {
      const source = sources.shift();
      now = Math.max(now, source.startAt + 0.1);
      source.context.currentTime = now;
      source.onended();
    }
    await blocked;

    expect(resumed).toBe(true);
    player.stop();
  });

  it("releases a waiting producer immediately on stop", async () => {
    const player = new PcmPlayer({ prebuffer: 0 });
    player.setSampleRate(1000);

    for (let index = 0; index < 70; index += 1) player.push(block());
    const blocked = player.push(block());

    player.stop();
    await expect(blocked).resolves.toBeUndefined();
  });
});

describe("PcmPlayer drain", () => {
  it("fires onDrained after the last scheduled block", () => {
    const onDrained = vi.fn();
    const player = new PcmPlayer({ prebuffer: 0, onDrained });
    player.setSampleRate(1000);

    player.push(block());
    player.flush();
    expect(onDrained).not.toHaveBeenCalled();

    sources[0].onended();
    expect(onDrained).toHaveBeenCalledTimes(1);
  });

  it("fires for an empty stream", () => {
    const onDrained = vi.fn();
    const player = new PcmPlayer({ prebuffer: 2.5, onDrained });

    player.flush();
    expect(onDrained).toHaveBeenCalledTimes(1);
  });

  it("does not fire after stop", () => {
    const onDrained = vi.fn();
    const player = new PcmPlayer({ prebuffer: 0, onDrained });
    player.setSampleRate(1000);

    player.push(block());
    player.flush();
    const source = sources[0];

    player.stop();
    source.onended();

    expect(onDrained).not.toHaveBeenCalled();
  });
});
