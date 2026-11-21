// One mapping from raw RMS level (0..1) to a 0..1 display ratio.
// Both the dictation meter and the Q&A mic panel read the same number, so the
// two screens never disagree about how loud the microphone is.

const LEVEL_GAIN = 13;
const LEVEL_CURVE = 0.55;

export function levelRatio(level) {
  const value = Math.max(0, Number(level) || 0);
  return Math.min(1, Math.pow(value * LEVEL_GAIN, LEVEL_CURVE));
}
