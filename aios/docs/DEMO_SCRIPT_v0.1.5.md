# AIOS v0.1.5 — 2-Minute Demo Script

## Goal
Show that memory is stable, measurable, and production-ready.

## 0) Setup (10s)
```bash
cd aios
```

## 1) Health check (20s)
```bash
make doctor
```
Narration:
- "Doctor now checks guard/store AND memory backend read/write."
- Expect: `ok=true`, includes `memory_backend` + `memory_rw`.

## 2) Memory write/read API flow (45s)
Run dashboard:
```bash
make dashboard
```
Open: `http://127.0.0.1:8787`

In UI:
- Add memory text in Chat Training Examples or Memory API flow
- Search with a related query

Narration:
- "This proves end-to-end memory add/search works through API, not just unit internals."

## 3) Latency benchmark (30s)
```bash
make bench-memory
make bench-memory-check
```
Narration:
- "We track p95 search latency and enforce threshold in CI."
- "Current threshold: 80ms; current run is far below."

## 4) CI quality lock (15s)
Show workflow summary:
- `test-and-smoke`
- `memory-profile` (tests + doctor + latency threshold)

Narration:
- "Any memory regression now fails CI before release."

## 5) Close (10s)
- "v0.1.5 = stable memory + observability + CI guardrails."
