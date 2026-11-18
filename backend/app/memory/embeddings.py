"""Text -> vector. Everything depends on the Embedder protocol, never on a vendor SDK."""
from __future__ import annotations

import sys
import zlib
from typing import Protocol

import numpy as np

from app.config import Settings
from app.memory.text import tokenize


class Embedder(Protocol):
    id: str   # identifies the vector space; stored with the index so that vectors are never mixed
    dim: int

    def embed(self, texts: list[str]) -> np.ndarray:
        """Return an (n, dim) float32 array of L2-normalised vectors."""


class HashingEmbedder:
    """Offline, deterministic fallback: hashed word unigrams+bigrams (sign hashing), sublinear tf, L2-normalised.
    Weaker than a neural model but needs no key and no download, so tests and demos always work."""

    def __init__(self, dim: int = 1024):
        self.dim = dim
        self.id = f"hash-{dim}"

    def _features(self, text: str) -> list[str]:
        toks = tokenize(text)
        return toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for f in self._features(t):
                h = zlib.crc32(f.encode("utf-8"))
                out[i, h % self.dim] += 1.0 if (h >> 16) & 1 else -1.0
        out = np.sign(out) * np.log1p(np.abs(out))
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.maximum(norms, 1e-9)


class OpenAIEmbedder:
    def __init__(self, api_key: str, model: str, batch_size: int = 96):
        from openai import OpenAI  # lazy import

        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._batch = batch_size
        self.id = f"openai:{model}"
        self.dim = 0  # set after the first call

    def embed(self, texts: list[str]) -> np.ndarray:
        vecs: list[list[float]] = []
        for i in range(0, len(texts), self._batch):
            resp = self._client.embeddings.create(model=self._model, input=texts[i:i + self._batch])
            vecs += [d.embedding for d in resp.data]
        arr = np.asarray(vecs, dtype=np.float32)
        if arr.size:
            self.dim = arr.shape[1]
            arr /= np.maximum(np.linalg.norm(arr, axis=1, keepdims=True), 1e-9)
        return arr


def get_embedder(settings: Settings) -> Embedder:
    if settings.embedder == "openai" or (settings.embedder == "auto" and settings.openai_api_key):
        if not settings.openai_api_key:
            raise RuntimeError("EMBEDDER=openai requires OPENAI_API_KEY")
        return OpenAIEmbedder(settings.openai_api_key, settings.embed_model)
    print("[memory] using the offline HashingEmbedder (no OPENAI_API_KEY)", file=sys.stderr)
    return HashingEmbedder()
