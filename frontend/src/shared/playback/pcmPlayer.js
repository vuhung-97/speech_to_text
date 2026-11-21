// Web Audio player for a never-ending PCM stream.
//
// Blocks are buffered until a short pre-roll (default 2.5 s) is available, then
// scheduled slightly ahead of the clock. Memory is bounded by the pre-roll plus
// the scheduling backlog, never by the document length. `stop()` releases the
// AudioContext.

const MIN_LEAD_SEC = 0.12;   // schedule at least this far in the future
const MAX_BACKLOG_SEC = 5;   // resync if scheduling drifts too far ahead
const MAX_QUEUED_SEC = 8;    // hard cap on buffered audio (memory guard)

export class PcmPlayer {
  constructor({ volume = 1, prebuffer = 2.5 } = {}) {
    this.volume = volume;
    this.prebuffer = Math.max(0, prebuffer);
    this._context = null;
    this._gain = null;
    this._sources = new Set();
    this._pending = [];
    this._nextTime = 0;
    this._queued = 0;
    this._started = false;
    this._stopped = false;
    this._sampleRate = 48_000;
  }

  get playing() {
    return Boolean(this._context) && (this._queued > 0 || this._pending.length > 0);
  }

  get bufferedSeconds() {
    return this._queued;
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

  push(float32) {
    if (this._stopped || !float32?.length) return;
    const duration = float32.length / this._sampleRate;

    if (!this._started) {
      this._pending.push(float32);
      this._queued += duration;
      if (this._queued < this.prebuffer) return;
      this._flush();
      return;
    }

    if (this._queued > MAX_QUEUED_SEC) return; // drop instead of growing memory
    this._schedule(float32);
  }

  /** Call when the stream ended so a short answer still plays. */
  flush() {
    if (!this._started && this._pending.length) this._flush();
  }

  _flush() {
    const blocks = this._pending;
    this._pending = [];
    this._queued = 0;
    this._started = true;
    for (const block of blocks) this._schedule(block);
  }

  _schedule(float32) {
    const context = this._ensureContext();
    const buffer = context.createBuffer(1, float32.length, this._sampleRate);
    buffer.copyToChannel(float32, 0);

    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(this._gain);

    const now = context.currentTime;
    if (this._nextTime < now + MIN_LEAD_SEC) {
      this._nextTime = now + MIN_LEAD_SEC; // start or recover from underrun
    }
    if (this._nextTime - now > MAX_BACKLOG_SEC) {
      this._nextTime = now + MIN_LEAD_SEC;
    }

    source.start(this._nextTime);
    this._nextTime += buffer.duration;
    this._queued += buffer.duration;
    this._sources.add(source);

    source.onended = () => {
      this._sources.delete(source);
      this._queued = Math.max(0, this._queued - buffer.duration);
    };
  }

  stop() {
    this._stopped = true;
    this._pending = [];
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
