"""Public entry point for the SQLite FAQ adapter.

The repository (:mod:`.sqlite_faq_repo`) and the in-RAM matcher
(:mod:`.sqlite_faq_matcher`) live in separate modules; this facade keeps the
historical import path used by ``main.py``, tools and tests.
"""

from __future__ import annotations

from ...domain.faq.normalize import normalize_question
from .sqlite_faq_matcher import (LEXICAL_WEIGHT, RERANK_POOL,
                                 SqliteFaqMatcher)
from .sqlite_faq_repo import SqliteFaqRepository

__all__ = ["LEXICAL_WEIGHT", "RERANK_POOL", "SqliteFaqMatcher",
           "SqliteFaqRepository", "normalize_question"]
