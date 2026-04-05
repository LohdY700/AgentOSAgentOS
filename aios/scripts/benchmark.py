#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import resource
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aios_core.bus import EventBus  # noqa: E402
from aios_core.events import Event  # noqa: E402
from aios_core.guard import GuardConfig, ProcessGuard  # noqa: E402
from aios_core.metrics import Metrics  # noqa: E402


async def run_benchmark() -> dict[str, float | int]:
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

    # Linux ru_maxrss is KB
    metrics.memory_idle_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

    out = metrics.snapshot()
    await bus.stop()
    return out


if __name__ == "__main__":
    result = asyncio.run(run_benchmark())
    print(json.dumps(result, ensure_ascii=False))
