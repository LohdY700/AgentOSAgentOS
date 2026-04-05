# AIOS Architecture (Phase 1)

## High-level
AIOS Phase 1 is an **event-first runtime skeleton** focused on reliability and observability.

Core components:
- `Event` envelope (`aios_core.events`)
- `EventBus` with retry/dead-letter/idempotency (`aios_core.bus`)
- `ProcessGuard` with `learning|strict` modes (`aios_core.guard`)
- Metrics and benchmark/report pipeline (`aios_core.metrics`, `scripts/benchmark*.py`)

## Event Envelope
Each event uses this canonical shape:
- `id` (uuid)
- `type`
- `source`
- `timestamp` (UTC ISO8601)
- `payload` (dict)
- `trace_id` (uuid)

This is used across system, security, and dead-letter flows.

## Event Flow
```text
Producer -> EventBus(topic queue) -> Handler
                        |              |
                        | success      | exception
                        v              v
                    mark-seen      retry (max_retries)
                                        |
                                        v
                              dead-letter event
```

## Guard Flow
```text
ps -eo comm= -> current process names
             -> compare with allowlist
             -> mode switch:
                - strict: emit security.process.anomaly per process
                - learning: write candidates file + emit summary event
```

## Reliability Controls
- Basic idempotency by `event.id`
- Retry budget (`max_retries`)
- Dead-letter topic for exceeded retry cases
- Unit tests cover idempotency/retry/dead-letter paths

## Observability
Benchmark/report pipeline outputs:
- `event_throughput`
- `event_latency_p95`
- `agent_restart_count`
- `guard_alert_count`
- `memory_idle_mb`

Report file:
- `docs/BENCHMARK_LATEST.md`

## Runtime Commands
- `make demo`
- `make bench`
- `make report`
- `make learning`
- `make test`

## Next (Phase 2+)
- Move from in-memory bus to pluggable transport (Unix socket / NATS)
- Add richer policy engine for guard rules
- Add persistent event store and replay support
- Add multi-agent orchestration and capability sandboxing
