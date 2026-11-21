"""Adapters that turn uploaded files into catalogue entries.

Each module owns one file format and returns plain value objects; validation,
de-duplication and persistence belong to the catalogue service.
"""

from __future__ import annotations
