"""Small exact-search vector store: a float32 matrix + item records, persisted as .npy + .jsonl."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class VectorStore:
    def __init__(self, dim: int):
        self.dim = dim
        self.items: list[dict] = []
        self.mat = np.zeros((0, dim), dtype=np.float32)
        self._pos: dict[str, int] = {}

    def __len__(self) -> int:
        return len(self.items)

    def upsert(self, items: list[dict], vectors: np.ndarray) -> None:
        """Insert or replace by item['id'] (so re-ingesting a changed document never duplicates it)."""
        assert len(items) == len(vectors)
        new_items, new_vecs = [], []
        for it, v in zip(items, vectors):
            if it["id"] in self._pos:
                i = self._pos[it["id"]]
                self.items[i] = it
                self.mat[i] = v
            else:
                new_items.append(it)
                new_vecs.append(v)
        if new_items:
            start = len(self.items)
            self.items += new_items
            self.mat = np.vstack([self.mat, np.asarray(new_vecs, dtype=np.float32)]) if len(self.mat) else np.asarray(new_vecs, dtype=np.float32)
            for j, it in enumerate(new_items):
                self._pos[it["id"]] = start + j

    def similarities(self, qvec: np.ndarray) -> np.ndarray:
        return self.mat @ qvec if len(self.items) else np.zeros(0, dtype=np.float32)

    def save(self, directory: Path, name: str) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        np.save(directory / f"{name}.npy", self.mat)
        with open(directory / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for it in self.items:
                f.write(json.dumps(it, ensure_ascii=False, default=str) + "\n")

    @classmethod
    def load(cls, directory: Path, name: str, dim: int) -> "VectorStore":
        s = cls(dim)
        mat = np.load(directory / f"{name}.npy")
        with open(directory / f"{name}.jsonl", encoding="utf-8") as f:
            items = [json.loads(l) for l in f if l.strip()]
        s.items, s.mat = items, mat.astype(np.float32)
        s._pos = {it["id"]: i for i, it in enumerate(items)}
        return s
