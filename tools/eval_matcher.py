"""Measure retrieval quality on a hand-written query set — no LLM involved.

    python tools/eval_matcher.py
    python tools/eval_matcher.py --file cauhoi_dapan.docx --queries tools/eval/docx_queries.json

It imports the outline into a throwaway database, asks every query, and reports
top-1/top-3/MRR plus the score spread between in-domain and off-topic questions.
That spread is what the answer floor (``DEFAULT_NEAR``) is calibrated against.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.adapters.embedding.onnx_e5 import build_embedder  # noqa: E402
from backend.adapters.importer.docx_faq import parse_docx  # noqa: E402
from backend.adapters.retrieval.sqlite_faq import (  # noqa: E402
    SqliteFaqMatcher, SqliteFaqRepository)
from backend.adapters.storage.sqlite import Database  # noqa: E402
from backend.adapters.storage.sqlite_faq_documents import (  # noqa: E402
    SqliteFaqDocumentRepository)
from backend.services.faq_documents import FaqDocumentsService  # noqa: E402
from backend.services.faq_service import FaqService  # noqa: E402

TENANT = "eval"
TOP_K = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default=str(ROOT / "cauhoi_dapan.docx"))
    parser.add_argument("--queries", default=str(ROOT / "tools" / "eval" / "docx_queries.json"))
    return parser.parse_args()


def load_queries(path: Path) -> list[dict[str, str | None]]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_matcher(outline: Path):
    folder = tempfile.TemporaryDirectory(prefix="faq-eval-")
    database = Database(Path(folder.name) / "eval.db")
    repository = SqliteFaqRepository(database)
    embedder, note = build_embedder()
    if note:
        print(f"! {note}")
    matcher = SqliteFaqMatcher(repository, embedder)
    catalogue = FaqService(repository, matcher, embedder)
    documents = FaqDocumentsService(SqliteFaqDocumentRepository(database),
                                    repository, catalogue, matcher)
    pairs = parse_docx(outline.read_bytes())
    report = documents.import_document(TENANT, outline.name, pairs)
    catalogue.reindex(TENANT)
    print(f"nạp {report['total']} câu từ {outline.name} · model {matcher.model_id} "
          f"· dim {matcher.dim}")
    return folder, matcher


def run(matcher: SqliteFaqMatcher, queries: list[dict[str, str | None]]) -> int:
    ranks: list[int] = []
    in_domain: list[float] = []
    off_topic: list[float] = []
    misses: list[str] = []

    for item in queries:
        question = str(item["question"])
        expected = item.get("expected")
        result = matcher.match(question, TENANT, k=TOP_K)
        ranked = []
        if result.matched:
            ranked.append(result.matched)
        ranked.extend(result.candidates)
        codes = [match.entry.source_ref for match in ranked]
        best_score = ranked[0].score if ranked else 0.0

        if expected is None:
            off_topic.append(best_score)
            print(f"  [lạc đề] {best_score:.3f}  {question}")
            continue

        in_domain.append(best_score)
        rank = codes.index(str(expected)) + 1 if str(expected) in codes else 0
        if rank:
            ranks.append(rank)
        else:
            misses.append(f"{question} → cần {expected}, nhận {codes[0] if codes else '—'}")
        mark = "✓" if rank == 1 else ("≈" if rank else "✗")
        found = codes[0] if codes else "—"
        print(f"  {mark} cos={best_score:.3f} hạng={rank or '—':>2}  {question}"
              f"  [{found}]")

    total = len(ranks)
    top1 = sum(1 for rank in ranks if rank == 1)
    top3 = sum(1 for rank in ranks if rank <= TOP_K)
    mrr = sum(1.0 / rank for rank in ranks) / len(ranks) if ranks else 0.0
    print()
    print(f"top-1 {top1}/{total} · top-{TOP_K} {top3}/{total} · MRR {mrr:.3f}")
    if in_domain:
        print(f"điểm trong phạm vi: min {min(in_domain):.3f} · max {max(in_domain):.3f}")
    if off_topic:
        print(f"điểm câu lạc đề:   min {min(off_topic):.3f} · max {max(off_topic):.3f}")
    print(f"ngưỡng hiện tại: chắc chắn {matcher.threshold:.2f} · "
          f"sàn {matcher.near_threshold:.2f}")
    for line in misses:
        print(f"  trượt: {line}")
    return 0


def main() -> int:
    args = parse_args()
    outline = Path(args.file)
    if not outline.is_file():
        print(f"! không thấy tệp: {outline}")
        return 1
    folder, matcher = build_matcher(outline)
    try:
        return run(matcher, load_queries(Path(args.queries)))
    finally:
        folder.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
