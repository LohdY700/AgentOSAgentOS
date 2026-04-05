# AIOS v0.1.0 (Draft Release Notes)

## Highlights
- Introduced **event-first runtime skeleton** for AIOS.
- Added canonical event envelope with trace support.
- Added in-memory event bus with:
  - idempotency guard
  - retry handling
  - dead-letter routing
- Added `ProcessGuard` with `strict` and `learning` modes.
- Added benchmark and markdown report generation pipeline.
- Added unit tests for core reliability paths.
- Added CI workflow for test + benchmark smoke + report generation.

## New Commands
```bash
make demo
make bench
make report
make learning
make test
```

## Core Files Added
- `src/aios_core/events.py`
- `src/aios_core/bus.py`
- `src/aios_core/guard.py`
- `src/aios_core/metrics.py`
- `src/aios_core/config.py`
- `scripts/benchmark.py`
- `scripts/benchmark_report.py`
- `scripts/merge_allowlist.py`

## Documentation Added
- `docs/ARCHITECTURE.md`
- `docs/KNOWN_LIMITATIONS.md`
- `docs/DEMO_SCRIPT.md`
- `docs/RELEASE_CHECKLIST.md`
- `README.en.md`

## Known Limits
See `docs/KNOWN_LIMITATIONS.md`.

## Notes
This release focuses on proving architecture direction and developer workflow, not full production hardening.
