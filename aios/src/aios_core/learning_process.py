from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.request import urlopen, Request

from .learning import LearningInbox


@dataclass(slots=True)
class LearningNote:
    url: str
    note: str
    title: str
    summary: str
    created_at: str


def _strip_html(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
    if not m:
        return "Untitled"
    return re.sub(r"\s+", " ", unescape(m.group(1))).strip()[:180] or "Untitled"


def fetch_and_summarize(url: str, max_chars: int = 700) -> tuple[str, str]:
    req = Request(url, headers={"User-Agent": "AIOS-Learning/0.1"})
    with urlopen(req, timeout=10) as r:
        html = r.read(300_000).decode("utf-8", errors="ignore")
    title = _extract_title(html)
    text = _strip_html(html)
    summary = text[:max_chars]
    return title, summary


def process_learning_inbox(root_dir: Path, limit: int = 5) -> dict:
    inbox = LearningInbox(root_dir / "data" / "learning-inbox.jsonl")
    out_path = root_dir / "data" / "learning-notes.jsonl"
    items = inbox.list_recent(limit=limit)
    written = 0
    errors: list[dict] = []

    for row in items:
        url = str(row.get("url", "")).strip()
        note = str(row.get("note", "")).strip()
        if not url:
            continue
        try:
            title, summary = fetch_and_summarize(url)
            n = LearningNote(
                url=url,
                note=note,
                title=title,
                summary=summary,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(n), ensure_ascii=False) + "\n")
            written += 1
        except Exception as exc:  # noqa: BLE001
            errors.append({"url": url, "error": str(exc)})

    return {"ok": True, "processed": len(items), "written": written, "errors": errors}
