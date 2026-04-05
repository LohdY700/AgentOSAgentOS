from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Awaitable, Callable

from .events import Event
from .metrics import Metrics

EventHandler = Callable[[Event], Awaitable[None]]


@dataclass(slots=True)
class BusConfig:
    max_retries: int = 2
    dead_letter_topic: str = "dead-letter"


class EventBus:
    """In-memory pub/sub bus for phase-1 MVP with retry and dead-letter support."""

    def __init__(self, config: BusConfig | None = None, metrics: Metrics | None = None) -> None:
        self.config = config or BusConfig()
        self.metrics = metrics or Metrics()
        self._queues: dict[str, asyncio.Queue[Event]] = defaultdict(asyncio.Queue)
        self._tasks: list[asyncio.Task] = []
        self._seen_ids: set[str] = set()
        self._published_at: dict[str, float] = {}

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        async def _worker() -> None:
            q = self._queues[topic]
            while True:
                event = await q.get()

                # idempotency guard: only once per event id
                if event.id in self._seen_ids:
                    q.task_done()
                    continue

                try:
                    await handler(event)
                    self._seen_ids.add(event.id)
                    started = self._published_at.pop(event.id, None)
                    if started is not None:
                        self.metrics.record_event_latency((time.monotonic() - started) * 1000)
                except Exception:  # noqa: BLE001
                    attempts = int(event.payload.get("_attempt", 0))
                    if attempts < self.config.max_retries:
                        retry_payload = dict(event.payload)
                        retry_payload["_attempt"] = attempts + 1
                        retry_event = Event(
                            id=event.id,
                            type=event.type,
                            source=event.source,
                            timestamp=event.timestamp,
                            payload=retry_payload,
                            trace_id=event.trace_id,
                        )
                        await q.put(retry_event)
                    else:
                        dlq_payload = dict(event.payload)
                        dlq_payload["error"] = "max_retries_exceeded"
                        await self.publish(
                            self.config.dead_letter_topic,
                            Event.create(
                                event_type="event.dead_letter",
                                source="event-bus",
                                payload={"topic": topic, "event": dlq_payload, "event_id": event.id},
                                trace_id=event.trace_id,
                            ),
                        )
                        self._seen_ids.add(event.id)
                finally:
                    q.task_done()

        self._tasks.append(asyncio.create_task(_worker(), name=f"bus:{topic}"))

    async def publish(self, topic: str, event: Event) -> None:
        self._published_at.setdefault(event.id, time.monotonic())
        await self._queues[topic].put(event)

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
