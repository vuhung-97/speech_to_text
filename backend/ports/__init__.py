"""Ports: the contracts a service depends on, with no implementation attached.

Importing a port must stay cheap and framework-free, so a service can be tested
with a fake adapter and a future implementation (vector index, cloud TTS, …)
plugs in without touching controllers or UI.
"""

from .embedding import Embedder
from .faq import FaqMatcher, FaqRepository
from .sessions import SessionRepository
from .speech import SpeechSynthesizer

__all__ = [
    "Embedder",
    "FaqMatcher",
    "FaqRepository",
    "SessionRepository",
    "SpeechSynthesizer",
]
