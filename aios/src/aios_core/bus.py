from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Awaitable, Callable

from .events import Event

EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    """In-memory pub/sub bus for phase-1 MVP."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[Event]] = defaultdict(asyncio.Queue)
        self._tasks: list[asyncio.Task] = []
        self._seen_ids: set[str] = set()

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        async def _worker() -> None:
            q = self._queues[topic]
            while True:
                event = await q.get()
                # basic idempotency guard
                if event.id in self._seen_ids:
                    q.task_done()
                    continue
                self._seen_ids.add(event.id)
                try:
                    await handler(event)
                finally:
                    q.task_done()

        self._tasks.append(asyncio.create_task(_worker(), name=f"bus:{topic}"))

    async def publish(self, topic: str, event: Event) -> None:
        await self._queues[topic].put(event)

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
