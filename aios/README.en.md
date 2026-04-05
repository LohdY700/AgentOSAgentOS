# AIOS (AI-native OS) — Phase 1 Skeleton

AIOS is an experiment in building an **AI-native runtime** on top of a tiny Linux base.

Current direction:
- Event-first architecture (push over polling)
- Lightweight runtime and process guard
- Reproducible benchmark flow

## Quickstart
```bash
cd aios
make demo
make bench
make report
make test
```

## Guard Modes
- `strict` (default): emits anomaly events for unknown processes
- `learning`: discovers unknown process names and writes candidates to file

Configs:
- `config/guard-allowlist.json`
- `config/guard-learning.json`

Promote learning candidates into strict allowlist:
```bash
python3 scripts/merge_allowlist.py
```

## Benchmark Output
Benchmark returns 5 core metrics:
- `event_throughput`
- `event_latency_p95`
- `agent_restart_count`
- `guard_alert_count`
- `memory_idle_mb`

Generate markdown report:
```bash
python3 scripts/benchmark_report.py
```

## Project Scope (now)
This repository currently focuses on a Phase-1 skeleton:
- Event envelope + in-memory bus
- Retry + dead-letter handling
- Basic idempotency
- Process guard with learning->strict hardening flow
- Unit tests for core reliability paths
