"""Adapters: concrete implementations of the ports.

Each subpackage owns one external dependency (ONNX, SQLite, the TTS SDK) and is
the only place allowed to import it. Services receive adapters through
``app.state`` dependency injection.
"""
