from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class ChatExample:
    role: str
    text: str
    created_at: str


class ChatExampleStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, role: str, text: str) -> ChatExample:
        ex = ChatExample(role=role.strip(), text=text.strip(), created_at=datetime.now(timezone.utc).isoformat())
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(ex), ensure_ascii=False) + "\n")
        return ex

    def list_recent(self, limit: int = 20) -> list[dict]:
        if not self.path.exists():
            return []
        rows: list[dict] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rows.append(json.loads(line))
        return rows[-max(1, limit):]
