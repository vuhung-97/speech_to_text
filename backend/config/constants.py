"""Audio constants shared by capture, segmentation and engines."""

ASR_SAMPLE_RATE = 16_000
TTS_SAMPLE_RATE = 48_000

# Legacy alias kept for the capture/segmentation call sites.
SAMPLE_RATE = ASR_SAMPLE_RATE

BLOCK_DUR = 0.1  # seconds per analysis frame
BLOCK = int(SAMPLE_RATE * BLOCK_DUR)
