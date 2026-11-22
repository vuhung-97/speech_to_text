"""Audio constants shared by capture, segmentation and engines."""

ASR_SAMPLE_RATE = 16_000
TTS_SAMPLE_RATE = 48_000

# Sizes are configured in megabytes, stored and compared in bytes.
BYTES_PER_MB = 1024 * 1024

# Recognition modes: settings schema, CLI choices and the pipeline share these.
MODE_ACCURATE = "accurate"
MODE_REALTIME = "realtime"
MODES = (MODE_ACCURATE, MODE_REALTIME)

# Legacy alias kept for the capture/segmentation call sites.
SAMPLE_RATE = ASR_SAMPLE_RATE

BLOCK_DUR = 0.1  # seconds per analysis frame
BLOCK = int(SAMPLE_RATE * BLOCK_DUR)
