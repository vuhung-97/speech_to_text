"""Lexical scoring for the rerank stage: pure-Python BM25 over the catalogue.

Cosine similarity is good at meaning but blurry on near-identical curated
questions — "cấu trúc trạm chính" and "cấu trúc trạm vùng" differ by one token
and score almost the same. BM25 notices exactly that token, so the matcher uses
it only to *order* the top cosine candidates, never to accept an answer.

Tokens are folded (no diacritics, ``đ`` → ``d``) so a question typed or
recognised without accents still matches; no dependency is added, and an index
over a few thousand questions is cheap to build and query.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence

import numpy as np

K1 = 1.5
B = 0.75
MIN_TOKEN_LENGTH = 2

_TOKEN = re.compile(r"[a-z0-9]+(?:[-._][a-z0-9]+)*")

# Vietnamese function words plus the outline's own style verbs. Folded forms,
# because tokens are folded before lookup.
STOPWORDS = frozenset(
    """
    dong chi hay cho biet neu trinh bay phan tich dien giai chung minh so sanh
    danh gia gioi thieu mo ta lam ro
    ve cua va la gi cac nhung mot trong de voi khi tu co nhu the nao ra sao
    theo bi duoc cho boi tai tren duoi nay do vay thi ma nen cung
    """.split()
)


def fold(text: str) -> str:
    """Lowercase, strip diacritics and map ``đ`` to ``d``."""
    decomposed = unicodedata.normalize("NFD", (text or "").lower())
    without_marks = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn")
    return without_marks.replace("đ", "d")


def tokenize(text: str) -> list[str]:
    """Content tokens of ``text``: folded, punctuation-free, stopwords removed."""
    return [
        token for token in _TOKEN.findall(fold(text))
        if len(token) >= MIN_TOKEN_LENGTH and token not in STOPWORDS
    ]


class Bm25Index:
    """Okapi BM25 over a fixed snapshot of documents, immutable after build."""

    def __init__(self, documents: Sequence[str]) -> None:
        self._documents = [tokenize(document) for document in documents]
        self._document_frequency: Counter[str] = Counter()
        for tokens in self._documents:
            self._document_frequency.update(set(tokens))
        total = sum(len(tokens) for tokens in self._documents)
        self._average_length = total / len(self._documents) if self._documents else 0.0

    @property
    def size(self) -> int:
        return len(self._documents)

    def scores(self, query: str) -> np.ndarray:
        """One BM25 score per document; zeros when the query shares no token."""
        values = np.zeros(len(self._documents), dtype=np.float32)
        query_tokens = set(tokenize(query))
        if not query_tokens:
            return values
        for index, tokens in enumerate(self._documents):
            values[index] = self._score(query_tokens, tokens)
        return values

    def _score(self, query_tokens: set[str], tokens: Sequence[str]) -> float:
        if not tokens:
            return 0.0
        frequencies = Counter(tokens)
        length_ratio = len(tokens) / self._average_length if self._average_length else 1.0
        score = 0.0
        for token in query_tokens:
            frequency = frequencies.get(token, 0)
            if not frequency:
                continue
            score += self._idf(token) * (
                frequency * (K1 + 1)
                / (frequency + K1 * (1 - B + B * length_ratio))
            )
        return score

    def _idf(self, token: str) -> float:
        documents = self.size
        frequency = self._document_frequency.get(token, 0)
        return math.log(1 + (documents - frequency + 0.5) / (frequency + 0.5))


__all__ = ["Bm25Index", "STOPWORDS", "fold", "tokenize"]
