"""Audio constants shared by capture, segmentation and engines."""

SAMPLE_RATE = 16_000
BLOCK_DUR = 0.1  # seconds per analysis frame
BLOCK = int(SAMPLE_RATE * BLOCK_DUR)
