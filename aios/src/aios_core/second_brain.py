from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .memory_backend import load_memory_backend


@dataclass(slots=True)
class SecondBrainConfig:
    vault_path: str
    patterns: list[str]
    max_chunk_chars: int
    min_chunk_chars: int
    push_to_memory_backend: bool
    index_path: str


def load_second_brain_config(root_dir: Path) -> SecondBrainConfig:
    cfg_path = root_dir / "config" / "second-brain.json"
    raw = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    return SecondBrainConfig(
        vault_path=str(raw.get("vault_path", "../second-brain-vault")),
        patterns=list(raw.get("patterns", ["**/*.md"])),
        max_chunk_chars=int(raw.get("max_chunk_chars", 900)),
        min_chunk_chars=int(raw.get("min_chunk_chars", 120)),
        push_to_memory_backend=bool(raw.get("push_to_memory_backend", True)),
        index_path=str(raw.get("index_path", "data/second-brain-index.jsonl")),
    )


def _chunks(text: str, max_chars: int, min_chars: int) -> list[str]:
    lines = [x.strip() for x in text.splitlines()]
    paras: list[str] = []
    cur: list[str] = []
    for ln in lines:
        if not ln:
            if cur:
                paras.append(" ".join(cur).strip())
                cur = []
            continue
        cur.append(ln)
    if cur:
        paras.append(" ".join(cur).strip())

    out: list[str] = []
    buf = ""
    for p in paras:
        if not p:
            continue
        candidate = (buf + "\n\n" + p).strip() if buf else p
        if len(candidate) <= max_chars:
            buf = candidate
            continue
        if buf and len(buf) >= min_chars:
            out.append(buf)
            buf = p
        else:
            for i in range(0, len(p), max_chars):
                part = p[i : i + max_chars].strip()
                if part and len(part) >= min_chars:
                    out.append(part)
            buf = ""
    if buf and len(buf) >= min_chars:
        out.append(buf)
    return out


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _load_existing_hashes(index_path: Path) -> set[str]:
    if not index_path.exists():
        return set()
    hashes: set[str] = set()
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            h = str(row.get("content_hash", "")).strip()
            if h:
                hashes.add(h)
        except Exception:
            continue
    return hashes


def index_second_brain(root_dir: Path) -> dict[str, Any]:
    cfg = load_second_brain_config(root_dir)
    vault = (root_dir / cfg.vault_path).resolve()
    index_path = root_dir / cfg.index_path
    index_path.parent.mkdir(parents=True, exist_ok=True)

    if not vault.exists():
        return {"ok": False, "error": f"vault not found: {vault}"}

    files: list[Path] = []
    for pat in cfg.patterns:
        files.extend(vault.glob(pat))
    files = sorted({p for p in files if p.is_file() and p.suffix.lower() == ".md"})

    old_hashes = _load_existing_hashes(index_path)
    rows: list[dict[str, Any]] = []
    new_for_memory: list[dict[str, Any]] = []

    for f in files:
        rel = str(f.relative_to(vault))
        text = f.read_text(encoding="utf-8", errors="ignore")
        parts = _chunks(text, max_chars=cfg.max_chunk_chars, min_chars=cfg.min_chunk_chars)
        for idx, part in enumerate(parts):
            h = _hash_text(f"{rel}::{idx}::{part}")
            row = {
                "source": "obsidian",
                "vault_relpath": rel,
                "chunk_id": idx,
                "text": part,
                "content_hash": h,
                "path": str(f),
            }
            rows.append(row)
            if h not in old_hashes:
                new_for_memory.append(row)

    with index_path.open("w", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")

    pushed = 0
    backend = "disabled"
    if cfg.push_to_memory_backend and new_for_memory:
        mem = load_memory_backend(root_dir)
        backend = mem.active
        for row in new_for_memory:
            mem.backend.add(
                text=row["text"],
                metadata={
                    "kind": "second_brain",
                    "source": "obsidian",
                    "vault_relpath": row["vault_relpath"],
                    "chunk_id": row["chunk_id"],
                    "content_hash": row["content_hash"],
                },
            )
            pushed += 1
    elif cfg.push_to_memory_backend:
        backend = load_memory_backend(root_dir).active

    return {
        "ok": True,
        "vault": str(vault),
        "files": len(files),
        "chunks": len(rows),
        "new_chunks": len(new_for_memory),
        "index_path": str(index_path),
        "memory_backend": backend,
        "pushed": pushed,
    }


def search_second_brain(root_dir: Path, query: str, limit: int = 5) -> dict[str, Any]:
    cfg = load_second_brain_config(root_dir)
    index_path = root_dir / cfg.index_path
    if not index_path.exists():
        return {"ok": True, "items": [], "index_path": str(index_path)}

    q_terms = [x for x in query.lower().split() if x]
    if not q_terms:
        return {"ok": False, "error": "query is empty"}

    scored: list[tuple[int, dict[str, Any]]] = []
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        text = str(row.get("text", "")).lower()
        score = sum(2 if t in text else 0 for t in q_terms)
        score += sum(1 for t in q_terms if t in str(row.get("vault_relpath", "")).lower())
        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    items = []
    for score, row in scored[: max(1, limit)]:
        items.append(
            {
                "score": score,
                "vault_relpath": row.get("vault_relpath", ""),
                "chunk_id": row.get("chunk_id", 0),
                "text": row.get("text", ""),
            }
        )

    return {"ok": True, "index_path": str(index_path), "items": items}
