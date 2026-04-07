from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class WikiConfig:
    wiki_dir: str
    inbox_path: str
    index_path: str


def load_wiki_config(root_dir: Path) -> WikiConfig:
    p = root_dir / "config" / "wiki-pipeline.json"
    raw = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return WikiConfig(
        wiki_dir=str(raw.get("wiki_dir", "wiki")),
        inbox_path=str(raw.get("inbox_path", "data/wiki-inbox.jsonl")),
        index_path=str(raw.get("index_path", "data/wiki-index.json")),
    )


def _slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    return s[:80] or "untitled"


def wiki_ingest(root_dir: Path, title: str, content: str, tags: list[str] | None = None) -> dict[str, Any]:
    cfg = load_wiki_config(root_dir)
    wiki_dir = root_dir / cfg.wiki_dir
    wiki_dir.mkdir(parents=True, exist_ok=True)

    slug = _slug(title)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    tgs = tags or []
    body = f"# {title}\n\n> created: {ts}\n> tags: {', '.join(tgs)}\n\n{content.strip()}\n"
    out = wiki_dir / f"{slug}.md"
    out.write_text(body, encoding="utf-8")

    inbox = root_dir / cfg.inbox_path
    inbox.parent.mkdir(parents=True, exist_ok=True)
    row = {"title": title, "slug": slug, "path": str(out.relative_to(root_dir)), "tags": tgs, "created_at": ts}
    with inbox.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return {"ok": True, "path": str(out.relative_to(root_dir)), "slug": slug}


def wiki_build_index(root_dir: Path) -> dict[str, Any]:
    cfg = load_wiki_config(root_dir)
    wiki_dir = root_dir / cfg.wiki_dir
    index_path = root_dir / cfg.index_path
    index_path.parent.mkdir(parents=True, exist_ok=True)

    items = []
    for p in sorted(wiki_dir.glob("*.md")):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        title = txt.splitlines()[0].lstrip("# ").strip() if txt else p.stem
        links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", txt)
        items.append({"title": title, "path": str(p.relative_to(root_dir)), "links": [u for _, u in links]})

    index = {"ok": True, "count": len(items), "items": items, "generated_at": datetime.now().isoformat()}
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "count": len(items), "index_path": str(index_path.relative_to(root_dir))}


def wiki_export_slide(root_dir: Path, slug: str) -> dict[str, Any]:
    cfg = load_wiki_config(root_dir)
    src = root_dir / cfg.wiki_dir / f"{slug}.md"
    if not src.exists():
        return {"ok": False, "error": "source not found"}
    txt = src.read_text(encoding="utf-8")
    title = txt.splitlines()[0].lstrip("# ").strip() if txt else slug
    out = root_dir / cfg.wiki_dir / f"{slug}.slides.md"
    content = f"---\nmarp: true\n---\n\n# {title}\n\n---\n\n" + "\n\n---\n\n".join([x.strip() for x in txt.split("\n\n") if x.strip()][1:6])
    out.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(out.relative_to(root_dir))}
