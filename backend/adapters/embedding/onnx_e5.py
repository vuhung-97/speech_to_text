"""ONNX multilingual-E5 embedder (offline, no torch, no extra dependency).

Files are vendored under ``models/embed/`` by ``tools/fetch_embed_model.py``:
``model.onnx`` (fp32 or quantized) and ``tokenizer.json``. E5 expects the
``query:``/``passage:`` prefixes, mean pooling over the attention mask and L2
normalisation — cosine similarity is then a plain dot product.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np

from ...config.paths import EMBED_DIR
from ...domain.faq.normalize import embed_input

MODEL_FILE = "model.onnx"
TOKENIZER_FILE = "tokenizer.json"
MODEL_ID = "multilingual-e5-small"
MODEL_VERSION = 1
DIM = 384
MAX_TOKENS = 256


class EmbeddingUnavailable(RuntimeError):
    """The ONNX model or tokenizer has not been installed."""


class OnnxE5Embedder:
    model_id = MODEL_ID
    version = MODEL_VERSION
    dim = DIM

    def __init__(self, directory: str | Path | None = None,
                 max_length: int = MAX_TOKENS) -> None:
        self.directory = Path(directory) if directory else EMBED_DIR
        self.max_length = int(max_length)
        self._session = None
        self._tokenizer = None
        self._input_names: tuple[str, ...] = ()
        self._output_name = ""

    # ------------------------------------------------------------ availability
    @property
    def model_path(self) -> Path:
        return self.directory / MODEL_FILE

    @property
    def tokenizer_path(self) -> Path:
        return self.directory / TOKENIZER_FILE

    @classmethod
    def files_present(cls, directory: str | Path | None = None) -> bool:
        folder = Path(directory) if directory else EMBED_DIR
        return (folder / MODEL_FILE).is_file() and (folder / TOKENIZER_FILE).is_file()

    def load(self) -> None:
        if self._session is not None:
            return
        if not self.files_present(self.directory):
            raise EmbeddingUnavailable(
                f"chưa có model embedding trong {self.directory} — chạy "
                "python tools/fetch_embed_model.py")
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self._tokenizer = Tokenizer.from_file(str(self.tokenizer_path))
        self._tokenizer.enable_truncation(max_length=self.max_length)
        pad_id = self._tokenizer.token_to_id("<pad>")
        self._tokenizer.enable_padding(
            pad_id=1 if pad_id is None else int(pad_id),
            pad_token="<pad>",
        )
        options = ort.SessionOptions()
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self._session = ort.InferenceSession(
            str(self.model_path),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )
        self._input_names = tuple(item.name for item in self._session.get_inputs())
        self._output_name = self._session.get_outputs()[0].name

    # ---------------------------------------------------------------- embedding
    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        return self._embed(texts, query=False)

    def embed_query(self, text: str) -> np.ndarray:
        return self._embed([text], query=True)[0]

    def _embed(self, texts: Sequence[str], *, query: bool) -> np.ndarray:
        self.load()
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)

        encoded = self._tokenizer.encode_batch(
            [embed_input(text, query=query) for text in texts])
        width = max(len(item.ids) for item in encoded)
        ids = np.zeros((len(encoded), width), dtype=np.int64)
        mask = np.zeros((len(encoded), width), dtype=np.int64)
        for row, item in enumerate(encoded):
            length = len(item.ids)
            ids[row, :length] = item.ids
            mask[row, :length] = item.attention_mask

        feed: dict[str, np.ndarray] = {}
        for name in self._input_names:
            if name == "input_ids":
                feed[name] = ids
            elif name == "attention_mask":
                feed[name] = mask
            elif name == "token_type_ids":
                feed[name] = np.zeros_like(ids)
        hidden = self._session.run([self._output_name], feed)[0]

        weights = mask[..., None].astype(np.float32)
        pooled = (hidden * weights).sum(axis=1) / np.maximum(weights.sum(axis=1), 1e-6)
        return _normalise(pooled)


def _normalise(matrix: np.ndarray) -> np.ndarray:
    values = np.asarray(matrix, dtype=np.float32)
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return values / norms


def build_embedder():
    """Use the ONNX model when installed, otherwise the offline hashing one."""
    from .hashing import HashingEmbedder

    if OnnxE5Embedder.files_present():
        embedder = OnnxE5Embedder()
        try:
            embedder.load()
            return embedder, ""
        except Exception as exc:  # corrupt files, missing runtime, bad graph…
            return HashingEmbedder(), f"embedding ONNX lỗi, dùng hashing: {exc}"
    return HashingEmbedder(), (
        "chưa có model embedding trong models/embed — đang dùng hashing fallback")


__all__ = [
    "EmbeddingUnavailable",
    "OnnxE5Embedder",
    "build_embedder",
]
