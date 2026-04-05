# AIOS v0.1.4 — Release Notes

## Highlights

This release hardens the memory stack for real-world usage and improves reproducibility for new environments.

### ✅ Memory backend hardening
- Stabilized langchain memory backend loading.
- Added backend-handle caching to reduce repeated warmup cost.
- Migrated embeddings import toward `langchain-huggingface` (with backward fallback).

### ✅ Stronger health checks
- `doctor` now validates memory layer in addition to guard/store:
  - memory backend status (`requested/active/fallback/note`)
  - memory read/write probe (`memory_rw`)

### ✅ Reproducible setup for semantic memory
- Added optional dependency group:
  - `pip install -e ".[memory]"`
- Includes: `langchain-community`, `langchain-huggingface`, `sentence-transformers`, `faiss-cpu`.

### ✅ CI coverage expanded
- Added CI job `memory-profile`:
  - install `.[memory]`
  - run full tests
  - run doctor check (including memory probe)

### ✅ Docs polish
- Added CI badge to README.
- Added `CI Profiles` section for quick understanding of workflow coverage.

---

## Validation summary
- Full unit tests: **20/20 passing**
- Smoke test on clean venv: **pass**
- Doctor result: **ok=true**, memory backend and memory read/write checks passed.

## Tag
- `v0.1.4`
