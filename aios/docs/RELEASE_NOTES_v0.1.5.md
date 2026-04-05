# AIOS v0.1.5 — Release Notes

## Highlights

### ✅ Release quality lock for memory performance
- Added latency guard script: `scripts/check_memory_benchmark.py`
- New Make target: `make bench-memory-check`
- Enforces memory search p95 threshold (default: 80ms)

### ✅ CI now protects memory latency regressions
- `memory-profile` workflow now runs:
  - full tests
  - doctor checks
  - memory latency threshold check (`make bench-memory-check`)

### ✅ Developer UX updates
- README quickstart now includes `bench-memory-check`
- Added release notes for this version

## Validation
- Tests pass: 22/22
- `make bench-memory-check`: pass

## Tag
- `v0.1.5`
