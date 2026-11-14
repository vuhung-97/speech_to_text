"""No-catalogue matcher: the honest default until the FAQ index is built.

Every question is unanswered, so the UI shows the fallback text plus the
"chưa trả lời" worklist entry. This keeps the whole conversation loop testable
end-to-end before any embedding model exists.
"""

from __future__ import annotations

from ...domain.faq.models import DEFAULT_NEAR, DEFAULT_THRESHOLD, FaqResult


class NullFaqMatcher:
    """Always returns "no match", with configurable thresholds for the UI."""

    def __init__(self, threshold: float = DEFAULT_THRESHOLD,
                 near_threshold: float = DEFAULT_NEAR) -> None:
        self.threshold = float(threshold)
        self.near_threshold = float(near_threshold)

    def match(self, question: str, tenant: str, k: int = 3) -> FaqResult:
        return FaqResult(
            matched=None,
            candidates=(),
            threshold=self.threshold,
            near_threshold=self.near_threshold,
        )


__all__ = ["NullFaqMatcher"]
