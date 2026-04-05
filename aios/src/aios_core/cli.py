from __future__ import annotations

import argparse
import asyncio
import json
import logging
import resource

from .bus import EventBus
from .events import Event
from .guard import GuardConfig, ProcessGuard
from .metrics import Metrics

logging.basicConfig(level=logging.INFO, format="%(message)s")


async def _cmd_demo() -> None:
    print("AIOS demo starting")
    metrics = Metrics()
    bus = EventBus(metrics=metrics)

    async def on_system(event: Event) -> None:
        print("[system]", event.to_json())

    async def on_security(event: Event) -> None:
        metrics.guard_alert_count += 1
        print("[security]", event.to_json())

    async def on_dead_letter(event: Event) -> None:
        print("[dead-letter]", event.to_json())

    bus.subscribe("system", on_system)
    bus.subscribe("security", on_security)
    bus.subscribe("dead-letter", on_dead_letter)

    await bus.publish("system", Event.create("system.boot", "aios", {"status": "ok"}))

    guard = ProcessGuard(
        GuardConfig(allowed={"systemd", "bash", "python3", "ps", "sh", "sleep"}),
        bus,
    )
    unknown = await guard.watch_once()
    print(json.dumps({"unknown_process_count": len(unknown)}))

    await asyncio.sleep(0.3)
    metrics.memory_idle_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print(json.dumps(metrics.snapshot(), ensure_ascii=False))
    await bus.stop()


async def _cmd_benchmark() -> None:
    metrics = Metrics()
    bus = EventBus(metrics=metrics)

    async def on_system(_: Event) -> None:
        return

    async def on_security(_: Event) -> None:
        metrics.guard_alert_count += 1

    async def on_dead_letter(_: Event) -> None:
        return

    bus.subscribe("system", on_system)
    bus.subscribe("security", on_security)
    bus.subscribe("dead-letter", on_dead_letter)

    for i in range(100):
        await bus.publish("system", Event.create("benchmark.tick", "bench", {"idx": i}))

    guard = ProcessGuard(
        GuardConfig(allowed={"systemd", "bash", "python3", "ps", "sh", "sleep"}),
        bus,
    )
    await guard.watch_once()

    await asyncio.sleep(0.2)
    metrics.memory_idle_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print(json.dumps(metrics.snapshot(), ensure_ascii=False))
    await bus.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="AIOS core tools")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo", help="run phase-1 demo flow")
    sub.add_parser("benchmark", help="run mini benchmark and output JSON metrics")

    args = parser.parse_args()

    if args.cmd == "demo":
        asyncio.run(_cmd_demo())
    elif args.cmd == "benchmark":
        asyncio.run(_cmd_benchmark())


if __name__ == "__main__":
    main()
