# AIOS Changelog

## v0.1.2 (in progress)
- Added local event-store pruning script (`scripts/prune_event_store.py`).
- Added `make store-prune` target.
- Added unit test for prune behavior.
- Added tunable event-store config via `config/event-store.json`.
- CLI now supports `--store-config` for per-device thresholds.
- Added presets: `event-store.low-ram.json` and `event-store.high-throughput.json`.
- Added Make targets for preset runs (`demo-lowram`, `bench-throughput`, etc.).
- Added `doctor` self-check command for guard/store config + writable probe.
- Added `make ci-smoke` target (test + doctor + benchmark) and wired CI workflow to use it.
- Added `make release-check` target (ci-smoke + report + replay-store) for pre-publish flow.
- Added local web dashboard (`make dashboard`) with health status + recent events for non-technical users.
- Dashboard now includes Agent Activity table (active/idle/down, last event, event count).

## v0.1.1
- Guard prefix allowlist (`allowed_prefixes`) added.
- Reduced strict-mode noise for dynamic process names (e.g. `kworker/*`).
- Added tests for prefix policy handling.

## v0.1.0
- Phase-1 event-first runtime skeleton.
- Event envelope + in-memory event bus.
- Retry + dead-letter + basic idempotency.
- Process guard with `learning|strict` flow.
- Benchmark/report pipeline, CI, demo docs.
