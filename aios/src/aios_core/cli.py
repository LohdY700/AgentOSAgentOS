from __future__ import annotations

import argparse
import asyncio
import json
import logging
import resource
from pathlib import Path

from .bus import EventBus
from .config import load_guard_config
from .events import Event
from .guard import ProcessGuard
from .metrics import Metrics

logging.basicConfig(level=logging.INFO, format="%(message)s")

DEFAULT_GUARD_CONFIG = Path(__file__).resolve().parents[2] / "config" / "guard-allowlist.json"


async def _cmd_demo(guard_config_path: Path) -> None:
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

    guard_cfg = load_guard_config(guard_config_path)
    guard = ProcessGuard(guard_cfg, bus)
    unknown = await guard.watch_once()
    print(json.dumps({"guard_mode": guard_cfg.mode, "unknown_process_count": len(unknown)}))

    await asyncio.sleep(0.3)
    metrics.memory_idle_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print(json.dumps(metrics.snapshot(), ensure_ascii=False))
    await bus.stop()


async def _cmd_benchmark(guard_config_path: Path) -> None:
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

    guard_cfg = load_guard_config(guard_config_path)
    guard = ProcessGuard(guard_cfg, bus)
    await guard.watch_once()

    await asyncio.sleep(0.2)
    metrics.memory_idle_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print(json.dumps(metrics.snapshot(), ensure_ascii=False))
    await bus.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="AIOS core tools")
    parser.add_argument(
        "--guard-config",
        default=str(DEFAULT_GUARD_CONFIG),
        help="path to guard allowlist json",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo", help="run phase-1 demo flow")
    sub.add_parser("benchmark", help="run mini benchmark and output JSON metrics")

    args = parser.parse_args()
    guard_cfg = Path(args.guard_config)

    if args.cmd == "demo":
        asyncio.run(_cmd_demo(guard_cfg))
    elif args.cmd == "benchmark":
        asyncio.run(_cmd_benchmark(guard_cfg))


if __name__ == "__main__":
    main()
