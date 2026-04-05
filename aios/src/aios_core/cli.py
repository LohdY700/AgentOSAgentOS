from __future__ import annotations

import argparse
import asyncio
import json
import logging
import resource
import time
from pathlib import Path

from .bus import EventBus
from .config import load_guard_config
from .events import Event
from .event_store import JsonlEventStore
from .guard import ProcessGuard
from .metrics import Metrics
from .store_config import load_event_store_config
from .doctor import render_doctor_json, doctor_exit_code
from .dashboard import run_dashboard
from .memory_backend import load_memory_backend

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_GUARD_CONFIG = ROOT_DIR / "config" / "guard-allowlist.json"
DEFAULT_STORE_CONFIG = ROOT_DIR / "config" / "event-store.json"


def _build_store(store_config_path: Path) -> JsonlEventStore:
    cfg = load_event_store_config(store_config_path)
    store_path = cfg.path if cfg.path.is_absolute() else ROOT_DIR / cfg.path
    return JsonlEventStore(
        store_path,
        max_lines=cfg.max_lines,
        keep_last=cfg.keep_last,
        prune_check_every=cfg.prune_check_every,
    )


async def _cmd_demo(guard_config_path: Path, store_config_path: Path) -> None:
    print("AIOS demo starting")
    metrics = Metrics()
    bus = EventBus(metrics=metrics, event_store=_build_store(store_config_path))

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


async def _cmd_benchmark(guard_config_path: Path, store_config_path: Path) -> None:
    metrics = Metrics()
    bus = EventBus(metrics=metrics, event_store=_build_store(store_config_path))

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




def _cmd_memory_benchmark(root_dir: Path, query: str, loops: int) -> None:
    mem = load_memory_backend(root_dir)
    probe = "memory-benchmark-probe"
    mem.backend.add(probe, {"kind": "benchmark_probe"})

    loops = max(1, int(loops))
    latencies: list[float] = []
    for _ in range(loops):
        t0 = time.perf_counter()
        mem.backend.search(query, limit=5)
        latencies.append((time.perf_counter() - t0) * 1000)

    latencies.sort()
    p50 = latencies[int(0.5 * (len(latencies) - 1))]
    p95 = latencies[int(0.95 * (len(latencies) - 1))]
    out = {
        "ok": True,
        "backend": mem.active,
        "loops": loops,
        "query": query,
        "latency_ms": {
            "avg": round(sum(latencies) / len(latencies), 3),
            "p50": round(p50, 3),
            "p95": round(p95, 3),
            "max": round(max(latencies), 3),
        },
    }
    print(json.dumps(out, ensure_ascii=False))

def _cmd_replay_store(store_config_path: Path) -> None:
    store = _build_store(store_config_path)
    rows = list(store.replay())
    by_topic: dict[str, int] = {}
    for topic, _ in rows:
        by_topic[topic] = by_topic.get(topic, 0) + 1
    print(json.dumps({"store": str(store.path), "events": len(rows), "topics": by_topic}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="AIOS core tools")
    parser.add_argument(
        "--guard-config",
        default=str(DEFAULT_GUARD_CONFIG),
        help="path to guard allowlist json",
    )
    parser.add_argument(
        "--store-config",
        default=str(DEFAULT_STORE_CONFIG),
        help="path to event store json config",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo", help="run phase-1 demo flow")
    sub.add_parser("benchmark", help="run mini benchmark and output JSON metrics")
    sub.add_parser("replay-store", help="summarize persisted events from local JSONL store")
    sub.add_parser("doctor", help="run self-check on guard/store configs and write access")
    mem_bench = sub.add_parser("memory-benchmark", help="benchmark memory search latency")
    mem_bench.add_argument("--query", default="sếp", help="query string for memory search")
    mem_bench.add_argument("--loops", type=int, default=20, help="number of repeated searches")
    dash = sub.add_parser("dashboard", help="start local web dashboard for non-technical users")
    dash.add_argument("--host", default="127.0.0.1")
    dash.add_argument("--port", type=int, default=8787)

    args = parser.parse_args()
    guard_cfg = Path(args.guard_config)
    store_cfg = Path(args.store_config)

    if args.cmd == "demo":
        asyncio.run(_cmd_demo(guard_cfg, store_cfg))
    elif args.cmd == "benchmark":
        asyncio.run(_cmd_benchmark(guard_cfg, store_cfg))
    elif args.cmd == "replay-store":
        _cmd_replay_store(store_cfg)
    elif args.cmd == "doctor":
        print(render_doctor_json(ROOT_DIR, guard_cfg, store_cfg))
        raise SystemExit(doctor_exit_code(ROOT_DIR, guard_cfg, store_cfg))
    elif args.cmd == "dashboard":
        run_dashboard(args.host, args.port, ROOT_DIR, guard_cfg, store_cfg)
    elif args.cmd == "memory-benchmark":
        _cmd_memory_benchmark(ROOT_DIR, args.query, args.loops)


if __name__ == "__main__":
    main()
