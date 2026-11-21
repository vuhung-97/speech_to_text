// Single owner of audible output: exactly one source may play at a time.
//
// Every playback source (cached WAV <audio>, PCM stream player, quick WAV)
// claims the channel before it starts; claiming synchronously stops the
// previous owner, so a new press never overlaps the audio it replaces. Owners
// check `isCurrentPlayback(key)` after awaits, so a late response from an old
// claim cannot resurrect itself. Pure module state, no React dependency.

let current = null; // { key, stop }
let sequence = 0;

export function beginPlayback(stop) {
  stopAllPlayback();
  sequence += 1;
  const key = sequence;
  current = { key, stop };
  return key;
}

export function isCurrentPlayback(key) {
  return current !== null && current.key === key;
}

export function endPlayback(key) {
  if (current && current.key === key) current = null;
}

export function stopAllPlayback() {
  if (!current) return;
  const { stop } = current;
  current = null;
  try {
    stop();
  } catch {
    // Releasing a finished source is best-effort; the owner still ends its claim.
  }
}
