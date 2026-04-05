# AIOS Phase 1 — MVP Hardening Plan

## Mục tiêu phase 1
Trong 7-14 ngày, đạt được bản MVP có thể chạy ổn định trong môi trường edge nhẹ.

## Deliverables (bắt buộc)

### D1) Event Bus nền tảng
- [ ] Chuẩn hoá event envelope:
  - `id`, `type`, `source`, `timestamp`, `payload`, `trace_id`
- [ ] Cơ chế pub/sub local (Unix socket hoặc lightweight broker)
- [ ] Retry policy + dead-letter queue đơn giản
- [ ] Idempotency key cho handler

**Definition of done:**
- 1 producer + 2 consumers chạy đồng thời
- xử lý duplicate event không gây side effects lặp

### D2) Agent Runtime tối thiểu
- [ ] Runner quản lý lifecycle agent (start/stop/restart)
- [ ] Resource guardrails (cpu/mem/timeout)
- [ ] Health check endpoint local

**Definition of done:**
- Agent treo sẽ bị restart theo policy
- Có log lifecycle rõ ràng

### D3) `aios-guard` v1
- [ ] Baseline process allowlist
- [ ] Phát hiện process lạ theo rule
- [ ] Emit event `security.process.anomaly`

**Definition of done:**
- Inject thử process lạ => event được đẩy + ghi log

### D4) Observability v1
- [ ] Structured log (JSON lines)
- [ ] 5 metrics cốt lõi:
  1) event_throughput
  2) event_latency_p95
  3) agent_restart_count
  4) guard_alert_count
  5) memory_idle_mb

**Definition of done:**
- Có script benchmark in ra số liệu chuẩn

## Ưu tiên triển khai
P0:
1. Event envelope + local pub/sub
2. Runtime lifecycle + timeout kill
3. Guard phát hiện process lạ

P1:
4. Retry + dead-letter
5. Metrics + benchmark

P2:
6. Tối ưu footprint + docs polish

## Rủi ro chính
- Event storm gây backlog
- Agent loop vô hạn chiếm CPU
- Guard false positive cao

## Giảm rủi ro
- Thêm rate limit theo source
- Hard timeout cho task
- Rule tuning theo mode `learning|strict`

## Mốc demo phase 1
Demo script:
1. Boot AIOS
2. Start producer tạo event hệ thống
3. Agent consumer phản hồi theo event
4. Spawn process lạ -> guard phát hiện -> alert event
5. In metrics cuối phiên
