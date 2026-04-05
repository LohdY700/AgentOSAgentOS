from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .events import Event


class JsonlEventStore:
    """Tiny append-only event store for local persistence/replay."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, topic: str, event: Event) -> None:
        payload = {"topic": topic, "event": asdict(event)}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def replay(self) -> Iterable[tuple[str, Event]]:
        if not self.path.exists():
            return []
        out: list[tuple[str, Event]] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                raw = row["event"]
                out.append(
                    (
                        row["topic"],
                        Event(
                            id=raw["id"],
                            type=raw["type"],
                            source=raw["source"],
                            timestamp=raw["timestamp"],
                            payload=raw["payload"],
                            trace_id=raw["trace_id"],
                        ),
                    )
                )
        return out
