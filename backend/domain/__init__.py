"""Domain layer: pure Python rules with no framework or I/O knowledge.

Everything here is importable and testable without FastAPI, numpy I/O or a
running model. Services orchestrate; controllers translate HTTP; adapters talk
to the outside world (SQLite, ONNX, the TTS SDK).
"""
