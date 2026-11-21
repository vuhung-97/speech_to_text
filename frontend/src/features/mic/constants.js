// Single source of truth for browser microphone constants.
// The worklet receives `packetSeconds` through processorOptions, so it never
// duplicates these values.

export const MIC_RATE = 16_000;
export const PACKET_SECONDS = 0.02;
export const GRACE_MS = 2_000;
export const INITIAL_GRACE_MS = 4_000;
export const HARD_LIMIT_MS = 12_000;
export const SPEECH_LEVEL = 0.05;
export const SILENT_LEVEL = 0.002;
export const LEVEL_SCALE = 220;

export const MIC_STORAGE_KEY = "mic.device";

export const WORKLET_URL = "/worklets/pcm-processor.js";
export const WS_AUDIO_PATH = `/ws/audio?sample_rate=${MIC_RATE}`;
