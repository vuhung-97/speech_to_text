// AudioWorklet: microphone float samples → 16 kHz mono PCM16, 20 ms packets.
//
// Resampling is a streaming linear interpolator: `pos` carries the fractional
// position across blocks and `prev` keeps the last sample, so no boundary is
// lost. The graph is muted (gain 0), so nothing is played back to the speakers.

const TARGET_RATE = 16000;
const PACKET_SECONDS = 0.02;

class PcmProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    this.targetRate = options?.processorOptions?.targetRate || TARGET_RATE;
    this.ratio = sampleRate / this.targetRate;
    this.packet = Math.round(this.targetRate * PACKET_SECONDS);
    this.acc = new Float32Array(this.packet * 4);
    this.accLength = 0;
    this.pos = 0;
    this.prev = 0;
    this.levelSum = 0;
    this.levelCount = 0;
    this.flushes = 0;
  }

  process(inputs) {
    const channel = inputs[0]?.[0];
    if (!channel || channel.length === 0) return true;

    if (Math.abs(this.ratio - 1) < 1e-6) {
      for (let index = 0; index < channel.length; index += 1) {
        this._push(channel[index]);
      }
      return true;
    }

    const length = channel.length;
    let pos = this.pos;
    while (pos < length - 1) {
      const base = Math.floor(pos);
      const frac = pos - base;
      const left = base < 0 ? this.prev : channel[base];
      const right = channel[base + 1] ?? channel[length - 1];
      this._push(left + (right - left) * frac);
      pos += this.ratio;
    }
    this.prev = channel[length - 1];
    this.pos = Math.max(0, pos - length);
    return true;
  }

  _push(sample) {
    this.levelSum += sample * sample;
    this.levelCount += 1;
    if (this.accLength >= this.acc.length) {
      const grown = new Float32Array(this.acc.length * 2);
      grown.set(this.acc);
      this.acc = grown;
    }
    this.acc[this.accLength] = sample;
    this.accLength += 1;
    if (this.accLength >= this.packet) this._flush();
  }

  _flush() {
    const pcm = new Int16Array(this.accLength);
    for (let index = 0; index < this.accLength; index += 1) {
      const value = Math.max(-1, Math.min(1, this.acc[index]));
      pcm[index] = value < 0 ? value * 0x8000 : value * 0x7fff;
    }
    this.port.postMessage({ type: "audio", buffer: pcm.buffer }, [pcm.buffer]);
    this.accLength = 0;

    this.flushes += 1;
    if (this.flushes % 5 === 0) { // ~10 level updates per second
      const level = Math.sqrt(this.levelSum / Math.max(1, this.levelCount));
      this.levelSum = 0;
      this.levelCount = 0;
      this.port.postMessage({ type: "level", value: level });
    }
  }
}

registerProcessor("pcm-processor", PcmProcessor);
