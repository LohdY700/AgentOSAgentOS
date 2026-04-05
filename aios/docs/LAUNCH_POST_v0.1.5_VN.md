# AIOS v0.1.5 (VN) — Post ngắn

AIOS v0.1.5 đã lên ✅

Điểm chính:
- Memory backend LangChain đã được harden (kèm fallback an toàn)
- `doctor` kiểm tra luôn memory backend + memory read/write
- Thêm benchmark memory latency (`make bench-memory`)
- CI khóa chất lượng bằng ngưỡng p95 (`make bench-memory-check`)

Kết quả hiện tại:
- Test: 22/22 pass
- p95 memory search ~17ms (threshold 80ms)

Repo: <https://github.com/LohdY700/AgentOSAgentOS>
Release notes: `docs/RELEASE_NOTES_v0.1.5.md`
