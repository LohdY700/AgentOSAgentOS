# AIOS (AI-native OS) — Bootstrap Pack

Mục tiêu: biến bản demo 65MB/5s boot thành hệ thống có thể demo công khai + có đường lên production.

## Trạng thái hiện tại
- ISO siêu nhẹ (~65MB)
- Boot nhanh (~5s)
- Có CLI nền tảng:
  - `aios` (dashboard)
  - `aios chat` (AI buddy)
  - `aios system` (JSON state)
  - `aios-guard` (phát hiện process lạ)
- Hướng kiến trúc đúng: **event push** thay vì polling

## Gói triển khai (đang chạy)
1. Phase 1 (MVP hardening): ổn định runtime + event bus + guard
2. Phase 2 (DX): tooling, logs, benchmark, test harness
3. Phase 3 (Public demo): docs, one-liner demo, roadmap + positioning

## Cấu trúc tài liệu
- `docs/PHASE1_PLAN.md` — backlog có thứ tự ưu tiên
- `docs/SKILL_MATRIX.md` — skill cần có + nguồn học + repo mẫu

## Nguyên tắc
- Event-first, deterministic, observable
- Ưu tiên an toàn khi cho agent quyền “vùng vẫy”
- Làm nhỏ, đo được, demo được

## Quickstart (Phase 1 skeleton)
```bash
cd aios
PYTHONPATH=src python3 -m aios_core.cli demo
PYTHONPATH=src python3 -m aios_core.cli benchmark
python3 scripts/benchmark.py
```

Output benchmark sẽ trả JSON với 5 metrics cốt lõi:
- `event_throughput`
- `event_latency_p95`
- `agent_restart_count`
- `guard_alert_count`
- `memory_idle_mb`
