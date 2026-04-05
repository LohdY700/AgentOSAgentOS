from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .bus import EventBus
from .events import Event


@dataclass(slots=True)
class GuardConfig:
    allowed: set[str]
    allowed_prefixes: tuple[str, ...] = ()
    poll_sec: float = 2.0
    mode: str = "strict"  # strict|learning
    learning_output: Path | None = None


class ProcessGuard:
    def __init__(self, config: GuardConfig, bus: EventBus) -> None:
        self.config = config
        self.bus = bus

    def _list_process_names(self) -> set[str]:
        out = subprocess.check_output(["ps", "-eo", "comm="], text=True)
        return {line.strip() for line in out.splitlines() if line.strip()}

    def _is_allowed(self, proc: str) -> bool:
        if proc in self.config.allowed:
            return True
        return any(proc.startswith(prefix) for prefix in self.config.allowed_prefixes)

    async def watch_once(self) -> list[str]:
        current = self._list_process_names()
        unknown = sorted(p for p in current if not self._is_allowed(p))

        if self.config.mode == "learning":
            if self.config.learning_output:
                self.config.learning_output.parent.mkdir(parents=True, exist_ok=True)
                self.config.learning_output.write_text("\n".join(unknown) + "\n", encoding="utf-8")
            await self.bus.publish(
                "security",
                Event.create(
                    event_type="security.process.learning",
                    source="aios-guard",
                    payload={"unknown_count": len(unknown)},
                ),
            )
            return unknown

        # strict mode: emit anomaly per process
        for proc in unknown:
            await self.bus.publish(
                "security",
                Event.create(
                    event_type="security.process.anomaly",
                    source="aios-guard",
                    payload={"process": proc},
                ),
            )
        return unknown

    async def watch_forever(self) -> None:
        while True:
            await self.watch_once()
            await asyncio.sleep(self.config.poll_sec)
