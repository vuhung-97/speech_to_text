// Web Audio player for a never-ending PCM stream.
//
// Received blocks are queued and scheduled only a few seconds ahead of the
// clock. Two rules keep the stream sequential and memory flat:
//   1. A block is never scheduled on top of another one (the old
//      "resync _nextTime" jump is gone — it made two parts of the same answer
//      play at once).
//   2. `push()` resolves immediately while the buffer is below the high-water
//      mark and only resolves again after playback drained to the low-water
//      mark; `pcmStream` awaits it, so TCP applies backpressure to the server
//      instead of buffering/dropping the whole document in RAM.
//
// `stop()` releases the AudioContext and any producer waiting for room.

const MIN_LEAD_SEC = 0.12; // schedule at least this far in the future
const SCHEDULE_AHEAD_SEC = 4; // never schedule audio further ahead than this
const HIGH_WATER_SEC = 6; // pause the producer above this buffered duration
const LOW_WATER_SEC = 3; // resume it once playback drained below this

export class PcmPlayer {
  constructor({ volume = 1, prebuffer = 2.5, onDrained = null, speed = 1 } = {}) {
    this.volume = volume;
    this.prebuffer = Math.max(0, prebuffer);
    this.speed = Math.min(3, Math.max(0.5, Number(speed) || 1));
    this._onDrained = onDrained;

    this._context = null;
    this._gain = null;
    this._sources = new Set();
    this._pending = [];
    this._pendingSeconds = 0;
    this._waiters = [];
    this._nextTime = 0;
    this._queued = 0;
    this._started = false;
    this._ended = false;
    this._drained = false;
    this._stopped = false;
    this._sampleRate = 48_000;
  }

  get playing() {
    return Boolean(this._context) && this.bufferedSeconds > 0;
  }

  get bufferedSeconds() {
    return this._queued + this._pendingSeconds;
  }

  /** Must be called from a user gesture the first time (browser autoplay rules). */
  async resume() {
    const context = this._ensureContext();
    if (context.state !== "running") await context.resume();
    return context;
  }

  _ensureContext() {
    if (this._context) return this._context;
    const Context = window.AudioContext || window.webkitAudioContext;
    this._context = new Context();
    this._gain = this._context.createGain();
    this._gain.gain.value = this.volume;
    this._gain.connect(this._context.destination);
    return this._context;
  }

  setVolume(value) {
    this.volume = Math.max(0, Math.min(1, Number(value) || 0));
    if (this._gain) this._gain.gain.value = this.volume;
  }

  setSampleRate(rate) {
    if (rate > 0) this._sampleRate = rate;
  }

  setSpeed(speed) {
    this.speed = Math.min(3, Math.max(0.5, Number(speed) || 1));
  }

  /**
   * Queue one block. Resolves when there is room for more audio; `pcmStream`
   * awaits it so the HTTP body stops being read while the player is full.
   */
  push(float32) {
    if (this._stopped || !float32?.length) return Promise.resolve();

    const duration = float32.length / this._sampleRate / this.speed;
    this._pending.push(float32);
    this._pendingSeconds += duration;
    this._pump();

    if (this.bufferedSeconds <= HIGH_WATER_SEC) return Promise.resolve();
    return new Promise((resolve) => this._waiters.push(resolve));
  }

  /** Call when the stream ended so a short answer still plays. */
  flush() {
    this._ended = true;
    this._pump();
    this._maybeDrain();
  }

  _pump() {
    if (this._stopped) return;

    if (!this._started) {
      // Keep pre-rolling until enough audio arrived; a finished stream starts
      // immediately even when it is shorter than the pre-roll.
      if (this._pendingSeconds < this.prebuffer && !this._ended) return;
      this._started = true;
    }

    const now = this._context ? this._context.currentTime : 0;
    while (this._pending.length && this._nextTime - now < SCHEDULE_AHEAD_SEC) {
      const block = this._pending.shift();
      this._pendingSeconds = Math.max(
        0,
        this._pendingSeconds - block.length / this._sampleRate / this.speed,
      );
      this._schedule(block);
    }
    this._releaseWaiters();
  }

  _schedule(float32) {
    const context = this._ensureContext();
    const buffer = context.createBuffer(1, float32.length, this._sampleRate);
    buffer.copyToChannel(float32, 0);

    const source = context.createBufferSource();
    source.buffer = buffer;
    source.playbackRate.value = this.speed;
    source.connect(this._gain);

    const now = context.currentTime;
    if (this._nextTime < now + MIN_LEAD_SEC) {
      this._nextTime = now + MIN_LEAD_SEC; // start or recover from underrun
    }
    // No "backlog reset": _pump only schedules within SCHEDULE_AHEAD_SEC, so
    // two blocks can never occupy the same moment.
    const clockDuration = buffer.duration / this.speed;
    source.start(this._nextTime);
    this._nextTime += clockDuration;
    this._queued += clockDuration;
    this._sources.add(source);

    source.onended = () => {
      this._sources.delete(source);
      this._queued = Math.max(0, this._queued - clockDuration);
      this._pump();
      this._maybeDrain();
    };
  }

  _releaseWaiters() {
    if (this.bufferedSeconds > LOW_WATER_SEC) return;
    const waiters = this._waiters;
    this._waiters = [];
    for (const resolve of waiters) resolve();
  }

  _releaseAllWaiters() {
    const waiters = this._waiters;
    this._waiters = [];
    for (const resolve of waiters) resolve();
  }

  _maybeDrain() {
    if (this._stopped || this._drained) return;
    if (!this._ended || this._pending.length || this._queued > 1e-6) return;
    this._drained = true;
    this._onDrained?.();
  }

  stop() {
    this._stopped = true;
    this._pending = [];
    this._pendingSeconds = 0;
    this._releaseAllWaiters();
    for (const source of this._sources) {
      try {
        source.stop();
      } catch {
        /* already stopped */
      }
    }
    this._sources.clear();
    this._queued = 0;
    this._nextTime = 0;
    this._started = false;
    if (this._context) {
      const context = this._context;
      this._context = null;
      this._gain = null;
      context.close().catch(() => {});
    }
  }
}

export default PcmPlayer;
