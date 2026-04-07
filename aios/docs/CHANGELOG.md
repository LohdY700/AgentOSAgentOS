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
- Added 2-tier approval policy docs + config and dashboard approval summary card.
- Added dashboard action buttons for non-technical users (`Run Health Check`, `Run Benchmark`).
- Added dashboard quick guidance card (`What to do now`) and `Copy Public Status` button.
- Added Learning Inbox flow (`Add Link` + `Learn Now`) with persisted learning notes.
- Added `Top 3 insights hôm nay` section in dashboard from learning notes.
- Added `Chat Training Examples` capture flow (user/assistant examples) in dashboard + API.
- Added conversation feedback loop (`👍/👎`) with quality score summary.
- Added configurable memory backend with `langchain` request + local fallback (`config/memory-backend.json`).
- Added memory APIs (`/api/memory/add`, `/api/memory/search`) and dashboard memory backend status.
- Added API endpoint `/api/approval/check?action=...` for policy decision queries.
- Stabilized langchain backend loading and reduced repeated warmup via backend handle caching.
- Migrated embeddings import toward `langchain-huggingface` (with backward fallback).
- Doctor now includes memory checks (backend status + read/write probe).
- Added optional dependency group `.[memory]` in `pyproject.toml` for reproducible setup.
- Added CI `memory-profile` job to validate `.[memory]` install + test + doctor checks.
- Updated README with CI badge and `CI Profiles` section.
- Added memory startup controls (`quiet_startup`, `preload_on_startup`) and exposed memory init timing/cache flags in dashboard status.
- Added CLI command `memory-benchmark` and `make bench-memory` for memory search latency tracking.
- Added README guidance for configuring `HF_TOKEN` to remove anonymous HF warnings and improve model warmup reliability.
- Added `.env.example` with recommended HF/memory startup environment variables.
- Added memory latency guard script (`scripts/check_memory_benchmark.py`) + `make bench-memory-check`.
- CI memory-profile now enforces memory latency threshold via `make bench-memory-check`.
- Added public/demo bundle for v0.1.5: `DEMO_SCRIPT_v0.1.5.md`, launch posts (VN/EN).
- Added Mission Control dashboard (`/mission-control`) with team lanes, notes, artifacts, and recent commits.
- Added Mission Control API endpoints: `/api/mission/status`, `/api/mission/note`.
- Added `docs/RAG_PIPELINE_v1.md` to standardize retrieval flow, metadata schema, query strategy, and rollout plan.
- Added local Obsidian second-brain flow (`config/second-brain.json`, `second-brain-index`, `second-brain-search`) to reduce token-heavy lookups.
- Upgraded Mission Control with Kanban-lite task status updates, blockers management, KPI cards, and one-click daily report generation.
- Added Mission Control auto-backup + auto-restore (`mission-control.backup.json`) to prevent data-loss frustration after crashes/restarts.
- Added automatic cache-busting for Mission Control JS (`/mission-control.js?v=<timestamp>`) to avoid stale frontend after updates.
- Added metadata-aware memory search filters (`kind`, `role`, `source`) in `/api/memory/search` and memory backends.

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
