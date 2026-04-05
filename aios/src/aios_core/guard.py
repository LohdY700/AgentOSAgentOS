from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass

from .events import Event
from .bus import EventBus


@dataclass(slots=True)
class GuardConfig:
    allowed: set[str]
    poll_sec: float = 2.0


class ProcessGuard:
    def __init__(self, config: GuardConfig, bus: EventBus) -> None:
        self.config = config
        self.bus = bus

    def _list_process_names(self) -> set[str]:
        out = subprocess.check_output(["ps", "-eo", "comm="], text=True)
        return {line.strip() for line in out.splitlines() if line.strip()}

    async def watch_once(self) -> list[str]:
        current = self._list_process_names()
        unknown = sorted(p for p in current if p not in self.config.allowed)
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
