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
- `docs/ARCHITECTURE.md` — kiến trúc phase 1
- `docs/KNOWN_LIMITATIONS.md` — giới hạn hiện tại
- `docs/DEMO_SCRIPT.md` — kịch bản demo 2 phút
- `docs/RELEASE_CHECKLIST.md` — checklist trước khi public
- `docs/RELEASE_NOTES_v0.1.0.md` — release notes draft
- `docs/RELEASE_COMMANDS.md` — lệnh phát hành/tag
- `docs/LAUNCH_POST_VN.md` — mẫu bài đăng tiếng Việt
- `docs/LAUNCH_POST_EN.md` — mẫu bài đăng tiếng Anh
- `README.en.md` — bản tiếng Anh ngắn

## Nguyên tắc
- Event-first, deterministic, observable
- Ưu tiên an toàn khi cho agent quyền “vùng vẫy”
- Làm nhỏ, đo được, demo được

## Quickstart (Phase 1 skeleton)
```bash
cd aios
make demo
make bench
make report
make test
```

(hoặc chạy tay)
```bash
PYTHONPATH=src python3 -m aios_core.cli demo
PYTHONPATH=src python3 -m aios_core.cli benchmark
python3 scripts/benchmark.py
python3 scripts/benchmark_report.py
```

Guard mode config:
- `config/guard-allowlist.json` (strict mặc định)
- `config/guard-learning.json` (learning mode)

Mode:
- `strict`: emit anomaly event theo từng process lạ
- `learning`: ghi danh sách process lạ ra `learning_output` để tinh chỉnh allowlist

Promote candidates:
```bash
python3 scripts/merge_allowlist.py
```

Output benchmark sẽ trả JSON với 5 metrics cốt lõi:
- `event_throughput`
- `event_latency_p95`
- `agent_restart_count`
- `guard_alert_count`
- `memory_idle_mb`
