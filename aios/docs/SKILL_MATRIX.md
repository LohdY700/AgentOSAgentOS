# AIOS Skill Matrix (Cần gì để build tốt)

## Core skills

### 1) Embedded Linux / Buildroot
- Mục đích: tối ưu image, init, package set
- Cần đạt: tự build/rebuild image reproducible
- Từ khoá GitHub:
  - `buildroot minimal linux`
  - `embedded linux init system`

### 2) Linux Systems Programming (Rust/Python)
- Mục đích: daemon runtime, signal handling, process supervision
- Cần đạt: runner an toàn + graceful shutdown
- Từ khoá GitHub:
  - `rust process supervisor`
  - `python asyncio daemon`

### 3) Event-Driven Architecture
- Mục đích: bỏ polling, xử lý push events ổn định
- Cần đạt: envelope/retry/idempotency/dead-letter
- Từ khoá GitHub:
  - `event bus rust`
  - `idempotent event handler`

### 4) Sandbox & Security
- Mục đích: cho agent quyền đủ dùng nhưng có rào chắn
- Cần đạt: seccomp/cgroups/capabilities cơ bản
- Từ khoá GitHub:
  - `linux seccomp examples`
  - `cgroups v2 sandbox`

### 5) Observability / Benchmarking
- Mục đích: chứng minh được hiệu năng và độ ổn định
- Cần đạt: metrics/log/benchmark reproducible
- Từ khoá GitHub:
  - `linux json logging`
  - `latency benchmark harness`

## Có thể tìm skill trên GitHub không?
**Có.**

Cách tìm nhanh:
1. Search theo capability + ngôn ngữ (vd: `event bus rust`).
2. Lọc repo có:
   - CI chạy xanh
   - issue/PR activity gần đây
   - docs rõ kiến trúc
3. Ưu tiên lấy **pattern** thay vì copy nguyên khối.

## Danh sách năng lực theo vai trò
- Builder (core): Buildroot + runtime + event bus
- Safety (guard): process anomaly + sandbox policy
- Productization: docs + benchmark + demo flow
