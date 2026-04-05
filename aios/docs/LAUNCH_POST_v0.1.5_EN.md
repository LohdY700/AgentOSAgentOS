# AIOS v0.1.5 (EN) — Short Launch Post

AIOS v0.1.5 is out ✅

Highlights:
- Hardened LangChain-first memory backend (with safe fallback)
- `doctor` now validates memory backend + memory read/write
- Added memory latency benchmark (`make bench-memory`)
- CI now enforces p95 latency threshold (`make bench-memory-check`)

Current status:
- Tests: 22/22 passing
- Memory search p95 ~17ms (threshold: 80ms)

Repo: <https://github.com/LohdY700/AgentOSAgentOS>
Release notes: `docs/RELEASE_NOTES_v0.1.5.md`
