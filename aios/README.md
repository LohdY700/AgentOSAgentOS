# AIOS (AI-native OS) — Bootstrap Pack

![CI](https://github.com/LohdY700/AgentOSAgentOS/actions/workflows/ci.yml/badge.svg)

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
- `docs/RELEASE_NOTES_v0.1.1.md` — patch notes (noise reduction)
- `docs/RELEASE_NOTES_v0.1.3.md` — dashboard UX + approval API
- `docs/CHANGELOG.md` — lịch sử thay đổi
- `docs/PUBLISH_CHECK.md` — checklist 60 giây trước khi publish
- `docs/RELEASE_COMMANDS.md` — lệnh phát hành/tag
- `docs/LAUNCH_POST_VN.md` — mẫu bài đăng tiếng Việt
- `docs/LAUNCH_POST_EN.md` — mẫu bài đăng tiếng Anh
- `docs/LAUNCH_POST_SHORT_VN.md` / `docs/LAUNCH_POST_SHORT_EN.md` — bản ngắn
- `docs/LAUNCH_POST_LONG_VN.md` / `docs/LAUNCH_POST_LONG_EN.md` — bản dài
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
make replay-store
make store-prune
make demo-lowram
make bench-throughput
make doctor
make bench-memory
make ci-smoke
make release-check
make dashboard
```

## CI Profiles
- `test-and-smoke`:
  - chạy smoke local target (`make ci-smoke`)
  - tạo benchmark report (`make report`)
- `memory-profile`:
  - cài optional deps memory (`pip install -e ".[memory]"`)
  - chạy test đầy đủ (`make test`)
  - chạy doctor check gồm memory backend read/write (`python -m aios_core.cli doctor`)

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

Event đã publish được append vào local JSONL store: `data/events.jsonl`.
Store có auto-prune mặc định (khi vượt ngưỡng sẽ giữ lại phần mới nhất) và có thể prune tay.
Ngưỡng này chỉnh trong `config/event-store.json` (`max_lines`, `keep_last`, `prune_check_every`).
Presets sẵn có:
- `config/event-store.low-ram.json` (thiết bị RAM thấp)
- `config/event-store.high-throughput.json` (luồng event dày)
Có thể xem thống kê nhanh bằng:
```bash
make replay-store
```
Và prune giữ lại 1000 event gần nhất:
```bash
make store-prune
```
Self-check nhanh cấu hình + quyền ghi:
```bash
make doctor
```
`doctor` trả exit code chuẩn: `0` (OK), `1` (có lỗi) để nhúng CI/healthcheck.

Dashboard trực quan cho người dùng không kỹ thuật:
```bash
make dashboard
# mở trình duyệt: http://127.0.0.1:8787
```
Trang này hiển thị trạng thái Healthy/Warning, bảng Active Agents (active/idle/down), Approval Policy tóm tắt, summary event store và 20 events gần nhất.
Có nút thao tác trực tiếp: **Run Health Check** và **Run Benchmark**.
Có thêm **Learning Inbox**: dán link, bấm **Add Link** rồi **Learn Now** để tạo ghi chú học tập.
Có thêm **Chat Training Examples** để nạp ví dụ hội thoại (user/assistant).
Có thêm feedback nhanh **👍/👎** để tính quality score hội thoại theo thời gian.
Dashboard cũng hiển thị **Top 3 insights hôm nay** từ learning notes.
Memory backend hỗ trợ cấu hình `langchain` (có fallback local), xem ở `config/memory-backend.json`.
Có thể bật/tắt preload + giảm noise startup qua:
- `langchain.quiet_startup` (mặc định `true`)
- `langchain.preload_on_startup` (mặc định `true`)

Production setup cho memory:
```bash
# cài optional deps cho semantic memory
pip install -e ".[memory]"

# kiểm tra nhanh guard/store + memory backend + memory read/write
make doctor
```

Gợi ý vận hành:
- Nếu `backend=langchain` nhưng thiếu libs, hệ thống tự fallback về `local`.
- Nên set `HF_TOKEN` để tránh warning anonymous request + tăng ổn định/rate-limit khi warmup lần đầu.

Ví dụ nhanh:
```bash
export HF_TOKEN=hf_xxx_your_token
make doctor
make bench-memory
```

Nếu muốn lưu lâu dài, thêm vào shell profile (`~/.bashrc` / `~/.zshrc`):
```bash
export HF_TOKEN=hf_xxx_your_token
```

Hoặc copy nhanh file mẫu env:
```bash
cp .env.example .env
```

Output benchmark sẽ trả JSON với 5 metrics cốt lõi:
- `event_throughput`
- `event_latency_p95`
- `agent_restart_count`
- `guard_alert_count`
- `memory_idle_mb`
 `event_latency_p95`
- `agent_restart_count`
- `guard_alert_count`
- `memory_idle_mb`
