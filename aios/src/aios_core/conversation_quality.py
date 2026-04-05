from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


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
