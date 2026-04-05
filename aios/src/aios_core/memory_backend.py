from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class BaseMemoryBackend:
    name: str = "base"

    def add(self, text: str, metadata: dict[str, Any] | None = None) -> None:  # pragma: no cover
        raise NotImplementedError

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError


class LocalJsonlMemoryBackend(BaseMemoryBackend):
    name = "local"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, text: str, metadata: dict[str, Any] | None = None) -> None:
        row = {"text": text.strip(), "metadata": metadata or {}}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        q = query.strip().lower()
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            text = str(row.get("text", ""))
            if q in text.lower():
                rows.append(row)
        return rows[-max(1, limit):][::-1]


class LangChainVectorMemoryBackend(BaseMemoryBackend):
    name = "langchain"

    def __init__(self, store_dir: str | Path, collection: str = "aios_memory") -> None:
        try:
            from langchain_community.vectorstores import FAISS
            try:
                from langchain_huggingface import HuggingFaceEmbeddings
            except Exception:  # noqa: BLE001
                from langchain_community.embeddings import HuggingFaceEmbeddings
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "langchain backend unavailable (install langchain-community + langchain-huggingface + sentence-transformers + faiss-cpu)"
            ) from exc

        self._FAISS = FAISS
        self._Emb = HuggingFaceEmbeddings
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.collection = collection
        self.index_dir = self.store_dir / collection

        self.emb = self._Emb(model_name="sentence-transformers/all-MiniLM-L6-v2")
        if self.index_dir.exists() and (self.index_dir / "index.faiss").exists():
            self.vs = self._FAISS.load_local(str(self.index_dir), self.emb, allow_dangerous_deserialization=True)
        else:
            self.vs = self._FAISS.from_texts(["seed memory"], embedding=self.emb, metadatas=[{"seed": True}])
            self.vs.save_local(str(self.index_dir))

    def add(self, text: str, metadata: dict[str, Any] | None = None) -> None:
        self.vs.add_texts([text], metadatas=[metadata or {}])
        self.vs.save_local(str(self.index_dir))

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        docs = self.vs.similarity_search(query, k=max(1, limit))
        out: list[dict[str, Any]] = []
        for d in docs:
            out.append({"text": d.page_content, "metadata": d.metadata})
        return out


@dataclass(slots=True)
class MemoryBackendHandle:
    backend: BaseMemoryBackend
    requested: str
    active: str
    fallback_used: bool
    note: str = ""


_BACKEND_CACHE: dict[str, MemoryBackendHandle] = {}


def load_memory_backend(root_dir: Path) -> MemoryBackendHandle:
    cfg_path = root_dir / "config" / "memory-backend.json"
    cfg_raw = cfg_path.read_text(encoding="utf-8") if cfg_path.exists() else "{}"
    cache_key = str(root_dir.resolve()) + "::" + cfg_raw
    cached = _BACKEND_CACHE.get(cache_key)
    if cached is not None:
        return cached

    cfg = json.loads(cfg_raw) if cfg_raw.strip() else {}

    requested = str(cfg.get("backend", "local")).lower()
    fallback = str(cfg.get("fallback", "local")).lower()
    local_path = cfg.get("local_path", "data/memory-local.jsonl")
    local_backend = LocalJsonlMemoryBackend(root_dir / local_path)

    if requested == "langchain":
        lc = cfg.get("langchain", {})
        try:
            backend = LangChainVectorMemoryBackend(
                store_dir=root_dir / lc.get("store_dir", "data/langchain-memory"),
                collection=str(lc.get("collection", "aios_memory")),
            )
            h = MemoryBackendHandle(backend=backend, requested=requested, active="langchain", fallback_used=False)
            _BACKEND_CACHE[cache_key] = h
            return h
        except Exception as exc:  # noqa: BLE001
            if fallback == "local":
                h = MemoryBackendHandle(
                    backend=local_backend,
                    requested=requested,
                    active="local",
                    fallback_used=True,
                    note=str(exc),
                )
                _BACKEND_CACHE[cache_key] = h
                return h
            raise

    h = MemoryBackendHandle(backend=local_backend, requested=requested, active="local", fallback_used=False)
    _BACKEND_CACHE[cache_key] = h
    return h
