from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Feedback:
    label: str  # good|bad
    note: str
    created_at: str


class FeedbackStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, label: str, note: str = "") -> Feedback:
        label = label.strip().lower()
        if label not in ("good", "bad"):
            raise ValueError("label must be good|bad")
        fb = Feedback(label=label, note=note.strip(), created_at=datetime.now(timezone.utc).isoformat())
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(fb), ensure_ascii=False) + "\n")
        return fb

    def list_recent(self, limit: int = 50) -> list[dict]:
        if not self.path.exists():
            return []
        rows: list[dict] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rows.append(json.loads(line))
        return rows[-max(1, limit):]


def quality_summary(rows: list[dict]) -> dict:
    good = sum(1 for r in rows if r.get("label") == "good")
    bad = sum(1 for r in rows if r.get("label") == "bad")
    total = good + bad
    score = round((good / total) * 100, 1) if total else 0.0
    return {"total": total, "good": good, "bad": bad, "score": score}


def _criterion_score(text: str, kind: str) -> int:
    t = text.strip()
    low = t.lower()
    if kind == "concise":
        if len(t) == 0:
            return 0
        if len(t) <= 220:
            return 2
        if len(t) <= 500:
            return 1
        return 0
    if kind == "actionable":
        hits = sum(1 for w in ["đã", "sẽ", "bước", "tiếp", "làm", "xong", "✅"] if w in low)
        return 2 if hits >= 2 else (1 if hits == 1 else 0)
    if kind == "role_tone":
        if "sếp" in low and ("em" in low or "su" in low):
            return 2
        if "sếp" in low or "em" in low:
            return 1
        return 0
    if kind == "clarity":
        lines = [x for x in t.splitlines() if x.strip()]
        bullets = sum(1 for ln in lines if ln.strip().startswith(("-", "•", "1)", "2)", "3)")))
        return 2 if bullets >= 1 else (1 if len(lines) <= 2 else 0)
    if kind == "no_fluff":
        fluff = ["rất vui", "hân hạnh", "có thể", "tùy trường hợp"]
        bad = sum(1 for w in fluff if w in low)
        return 2 if bad == 0 else (1 if bad == 1 else 0)
    return 0


def rubric_score(text: str) -> dict[str, Any]:
    criteria = ["concise", "actionable", "role_tone", "clarity", "no_fluff"]
    detail = {c: _criterion_score(text, c) for c in criteria}
    total = sum(detail.values())
    return {
        "total": total,
        "max": 10,
        "detail": detail,
        "pass": total >= 7,
    }


def build_daily_rubric_review(examples: list[dict], limit: int = 5) -> dict[str, Any]:
    assistant_rows = [x for x in examples if str(x.get("role", "")) == "assistant"]
    scored = []
    for row in assistant_rows:
        text = str(row.get("text", ""))
        rs = rubric_score(text)
        scored.append({"text": text, "created_at": row.get("created_at", ""), "rubric": rs})
    scored.sort(key=lambda x: int(x["rubric"]["total"]))
    return {"ok": True, "items": scored[: max(1, limit)]}
