from __future__ import annotations

import argparse
import json
import subprocess
import sys


def main() -> int:
    p = argparse.ArgumentParser(description="Run memory benchmark and enforce latency threshold")
    p.add_argument("--python", default=sys.executable, help="Python executable to run CLI")
    p.add_argument("--query", default="sếp")
    p.add_argument("--loops", type=int, default=20)
    p.add_argument("--threshold-ms", type=float, default=80.0, help="max allowed p95 latency in ms")
    args = p.parse_args()

    cmd = [
        args.python,
        "-m",
        "aios_core.cli",
        "memory-benchmark",
        "--query",
        args.query,
        "--loops",
        str(args.loops),
    ]
    out = subprocess.check_output(cmd, text=True)
    lines = [x.strip() for x in out.splitlines() if x.strip()]
    payload = json.loads(lines[-1])
    p95 = float(payload.get("latency_ms", {}).get("p95", 0.0))

    print(json.dumps({"ok": p95 <= args.threshold_ms, "p95_ms": p95, "threshold_ms": args.threshold_ms}, ensure_ascii=False))
    return 0 if p95 <= args.threshold_ms else 1


if __name__ == "__main__":
    raise SystemExit(main())
