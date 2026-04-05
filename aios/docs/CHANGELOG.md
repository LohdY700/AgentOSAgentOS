# AIOS Changelog

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
