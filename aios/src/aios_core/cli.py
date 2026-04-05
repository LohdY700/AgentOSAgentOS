from __future__ import annotations

import argparse
import asyncio
import json
import logging

from .bus import EventBus
from .events import Event
from .guard import GuardConfig, ProcessGuard

logging.basicConfig(level=logging.INFO, format="%(message)s")


async def _cmd_demo() -> None:
    print("AIOS demo starting")
    bus = EventBus()

    async def on_system(event: Event) -> None:
        print("[system]", event.to_json())

    async def on_security(event: Event) -> None:
        print("[security]", event.to_json())

    bus.subscribe("system", on_system)
    bus.subscribe("security", on_security)

    await bus.publish("system", Event.create("system.boot", "aios", {"status": "ok"}))

    guard = ProcessGuard(
        GuardConfig(allowed={"systemd", "bash", "python3", "ps", "sh", "sleep"}),
        bus,
    )
    unknown = await guard.watch_once()
    print(json.dumps({"unknown_process_count": len(unknown)}))

    await asyncio.sleep(0.3)
    await bus.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="AIOS core tools")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo", help="run phase-1 demo flow")

    args = parser.parse_args()

    if args.cmd == "demo":
        asyncio.run(_cmd_demo())


if __name__ == "__main__":
    main()
