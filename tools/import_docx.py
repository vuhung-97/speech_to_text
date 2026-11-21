"""Import a question/answer outline (``.docx``) into the catalogue — one command.

    python tools/import_docx.py --file cauhoi_dapan.docx
    python tools/import_docx.py --file cauhoi_dapan.docx --dry-run
    python tools/import_docx.py --file de_cuong_khac.docx --tenant acme

Re-running with an edited file updates the entries of that file instead of
adding duplicates (identity = file name + «Câu …» code). Embeddings are built
right after the import, so the Q&A screen can answer immediately; no LLM is
involved at any point.
"""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from ._shared import bootstrap
except ImportError:  # run as a script: python tools/import_docx.py
    from _shared import bootstrap

bootstrap()

from backend.adapters.embedding.onnx_e5 import build_embedder  # noqa: E402
from backend.adapters.importer.docx_faq import parse_docx  # noqa: E402
from backend.adapters.retrieval.sqlite_faq import (  # noqa: E402
    SqliteFaqMatcher, SqliteFaqRepository)
from backend.adapters.storage.sqlite import Database  # noqa: E402
from backend.adapters.storage.sqlite_faq_documents import (  # noqa: E402
    SqliteFaqDocumentRepository)
from backend.config.paths import DB_PATH  # noqa: E402
from backend.services.faq_documents import FaqDocumentsService  # noqa: E402
from backend.services.faq_service import FaqService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, help="đường dẫn tệp .docx")
    parser.add_argument("--db", default=str(DB_PATH), help="cơ sở dữ liệu SQLite")
    parser.add_argument("--tenant", default="local", help="workspace đích")
    parser.add_argument("--dry-run", action="store_true",
                        help="chỉ đọc tệp và in số câu, không ghi DB")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = Path(args.file)
    if not path.is_file():
        print(f"! không thấy tệp: {path}")
        return 1
    if path.suffix.lower() != ".docx":
        print("! chỉ nhận tệp .docx (tệp .doc cũ cần lưu lại dạng .docx)")
        return 1

    data = path.read_bytes()
    entries = parse_docx(data)
    if args.dry_run:
        print(f"đọc được {len(entries)} câu trong {path.name} — chưa ghi gì vào DB")
        for item in entries[:3]:
            print(f"  {item.code or '(không mã)'} · {item.question[:90]}")
        return 0

    database = Database(args.db)
    repository = SqliteFaqRepository(database)
    embedder, note = build_embedder()
    if note:
        print(f"! {note}")
    matcher = SqliteFaqMatcher(repository, embedder)
    catalogue = FaqService(repository, matcher, embedder)
    documents = FaqDocumentsService(SqliteFaqDocumentRepository(database),
                                    repository, catalogue, matcher)

    print(f"đang nạp {path.name} vào '{args.tenant}' (model: {matcher.model_id})…")
    report = documents.import_document(args.tenant, path.name, entries)
    document = report["document"]
    print(f"  bộ đề: {document['name']} ({document['id']}) · {report['reason']}")
    print(f"  tổng {report['total']} · thêm {report['added']} · "
          f"cập nhật {report['updated']} · bỏ qua {report['skipped']} · "
          f"tắt {report['stale']} · lỗi {len(report['errors'])}")
    for error in report["errors"][:10]:
        print(f"  ! dòng {error['row']} {error.get('code') or ''}: {error['error']}")

    indexed = catalogue.reindex(args.tenant)
    print(f"đã embedding {indexed['indexed']} câu · dim {indexed['dim']} · "
          f"model {indexed['model']}")
    print("xong — mở màn hình Hỏi đáp và đặt câu hỏi để kiểm tra.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
