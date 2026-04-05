from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class EventStoreConfig:
    path: Path
    max_lines: int = 5000
    keep_last: int = 1000
    prune_check_every: int = 200


def load_event_store_config(path: str | Path) -> EventStoreConfig:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    return EventStoreConfig(
        path=Path(data.get("path", "data/events.jsonl")),
        max_lines=int(data.get("max_lines", 5000)),
        keep_last=int(data.get("keep_last", 1000)),
        prune_check_every=int(data.get("prune_check_every", 200)),
    )
