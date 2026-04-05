from __future__ import annotations

import asyncio
import unittest

from aios_core.bus import BusConfig, EventBus
from aios_core.events import Event


class BusTests(unittest.IsolatedAsyncioTestCase):
    async def test_idempotency_same_event_id_once(self) -> None:
        bus = EventBus()
        seen: list[str] = []

        async def handler(event: Event) -> None:
            seen.append(event.id)

        bus.subscribe("topic", handler)
        ev = Event.create("x", "test", {"v": 1})
        await bus.publish("topic", ev)
        await bus.publish("topic", ev)
        await asyncio.sleep(0.1)
        await bus.stop()

        self.assertEqual(len(seen), 1)

    async def test_retry_then_success(self) -> None:
        bus = EventBus(config=BusConfig(max_retries=2))
        calls = {"n": 0}

        async def handler(_: Event) -> None:
            calls["n"] += 1
            if calls["n"] < 2:
                raise RuntimeError("boom")

        bus.subscribe("topic", handler)
        await bus.publish("topic", Event.create("x", "test", {}))
        await asyncio.sleep(0.2)
        await bus.stop()

        self.assertEqual(calls["n"], 2)

    async def test_dead_letter_on_exceeded_retry(self) -> None:
        bus = EventBus(config=BusConfig(max_retries=1))
        dlq: list[Event] = []

        async def bad_handler(_: Event) -> None:
            raise RuntimeError("always fail")

        async def dlq_handler(event: Event) -> None:
            dlq.append(event)

        bus.subscribe("topic", bad_handler)
        bus.subscribe("dead-letter", dlq_handler)

        await bus.publish("topic", Event.create("x", "test", {}))
        await asyncio.sleep(0.25)
        await bus.stop()

        self.assertEqual(len(dlq), 1)
        self.assertEqual(dlq[0].type, "event.dead_letter")


if __name__ == "__main__":
    unittest.main()
