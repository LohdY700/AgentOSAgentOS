#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from benchmark import run_benchmark  # type: ignore
import asyncio

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "guard-allowlist.json"
OUT = ROOT / "docs" / "BENCHMARK_LATEST.md"


def render_md(metrics: dict[str, object]) -> str:
    ts = datetime.now(timezone.utc).isoformat()
    lines = [
        "# AIOS Benchmark Report (Latest)",
        "",
        f"- Generated at (UTC): `{ts}`",
        f"- Guard mode: `{metrics.get('guard_mode', 'unknown')}`",
        "",
        "## Metrics",
        "",
        f"- event_throughput: **{metrics['event_throughput']}**",
        f"- event_latency_p95 (ms): **{metrics['event_latency_p95']}**",
        f"- agent_restart_count: **{metrics['agent_restart_count']}**",
        f"- guard_alert_count: **{metrics['guard_alert_count']}**",
        f"- memory_idle_mb: **{metrics['memory_idle_mb']}**",
        "",
        "## Raw JSON",
        "",
        "```json",
        json.dumps(metrics, ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    metrics = asyncio.run(run_benchmark(CFG))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render_md(metrics), encoding="utf-8")
    print(f"wrote {OUT}")
