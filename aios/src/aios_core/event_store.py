from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .events import Event


class JsonlEventStore:
    """Tiny append-only event store for local persistence/replay.

    Auto-prune behavior:
    - if line count exceeds `max_lines`, keep only the latest `keep_last` lines.
    - prune checks run every `prune_check_every` appends to avoid constant full-file scans.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        max_lines: int = 5000,
        keep_last: int = 1000,
        prune_check_every: int = 200,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_lines = max_lines
        self.keep_last = keep_last
        self.prune_check_every = max(1, prune_check_every)
        self._append_count = 0

    def append(self, topic: str, event: Event) -> None:
        payload = {"topic": topic, "event": asdict(event)}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

        self._append_count += 1
        if self._append_count % self.prune_check_every == 0:
            self._maybe_prune()

    def _maybe_prune(self) -> None:
        if self.max_lines < 1 or self.keep_last < 1 or not self.path.exists():
            return

        lines = self.path.read_text(encoding="utf-8").splitlines()
        if len(lines) <= self.max_lines:
            return

        kept = lines[-self.keep_last :]
        self.path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")

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
