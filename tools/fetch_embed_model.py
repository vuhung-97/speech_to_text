"""Download the E5 ONNX embedding model into ``models/embed/`` (one time).

    python tools/fetch_embed_model.py            # quantized (~50 MB)
    python tools/fetch_embed_model.py --full     # fp32 (~470 MB)

The backend runs fully offline after this; without it the catalogue falls back
to the deterministic hashing embedder (weaker on paraphrases, zero download).
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config.paths import EMBED_DIR  # noqa: E402

REPO = "Xenova/multilingual-e5-small"
QUANTIZED = "onnx/model_quantized.onnx"
FULL = "onnx/model.onnx"
TOKENIZER = "tokenizer.json"


def download(destination: Path, full: bool) -> None:
    from huggingface_hub import hf_hub_download

    destination.mkdir(parents=True, exist_ok=True)
    model_target = destination / "model.onnx"
    if model_target.is_file():
        print(f"đã có {model_target} — bỏ qua")
    else:
        remote = FULL if full else QUANTIZED
        print(f"tải {remote} từ {REPO}…")
        try:
            path = hf_hub_download(REPO, remote, local_dir=str(destination))
        except Exception as exc:  # network, gated repo, renamed file…
            print(f"! không tải được {remote}: {exc}")
            raise SystemExit(1) from exc
        shutil.move(path, model_target)
        print(f"✓ {model_target} ({model_target.stat().st_size / 1e6:.1f} MB)")

    tokenizer_target = destination / TOKENIZER
    if not tokenizer_target.is_file():
        print(f"tải {TOKENIZER}…")
        path = hf_hub_download(REPO, TOKENIZER, local_dir=str(destination))
        shutil.move(path, tokenizer_target)
        print(f"✓ {tokenizer_target}")

    print("xong. Chạy lại backend để dùng embedding thật.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default=str(EMBED_DIR), help="thư mục đích")
    parser.add_argument("--full", action="store_true", help="tải bản fp32")
    args = parser.parse_args()
    download(Path(args.dir), args.full)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
