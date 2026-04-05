# AIOS — Agent Evolution Plan (Snake Growth)

## Mục tiêu
Phát triển agent từ trạng thái "đã sống" sang trạng thái "tự tiến hóa có kiểm soát" — mô hình rắn càng dùng càng khôn, nhưng vẫn an toàn và đo được.

## Nguyên tắc
- Event-first, memory-driven, measurable
- Growth phải có guardrail (không tự trôi hành vi)
- Mọi tiến hóa đều có metric + rollback path

## Phase 1 — Foundation (1 tuần)
1) Memory Intelligence v1
- Metadata filter cho memory search (`kind`, `role`, `time range`)
- Dedupe memory khi add
- TTL/archival cho memory cũ

2) Agent Health API
- `/api/memory/health` (backend, init_ms, cache_hit, index size)
- `/api/agent/health` (event_rate, error_rate, restart_count)

3) Growth Metrics
- Memory hit-rate
- Response relevance proxy (feedback good/bad)
- Latency p50/p95

## Phase 2 — Adaptive Behavior (1–2 tuần)
1) Snake Stage System
- Stage 1: Head-only (rule-based)
- Stage 2: Growing (memory-assisted)
- Stage 3: Evolved (memory + policy adaptation)

2) Skill Unlock theo stage
- stage tăng => bật thêm skill đề xuất / tự động hóa nhẹ
- mỗi skill unlock cần explicit flag trong config

3) Learning Loop có kiểm duyệt
- agent đề xuất policy update (draft)
- owner duyệt rồi mới apply

## Phase 3 — Multi-Agent Expansion (2 tuần)
1) Vai trò hóa agent
- Scout Agent: tìm thông tin + tổng hợp
- Builder Agent: triển khai code/task
- Guard Agent: audit/log/risk

2) Orchestrator
- main agent phân task cho sub-agent theo role
- có score cho output từng agent

3) Shared Memory Bus
- namespace memory theo agent
- global memory cho insight chung

## Phase 4 — Productization (liên tục)
1) Demo mode "Snake Evolution"
- timeline tiến hóa theo ngày
- replay event quan trọng

2) Release discipline
- mỗi release phải có benchmark + doctor + latency gate

3) Safety hardening
- approval tier cho hành động nhạy cảm
- anomaly detector cho hành vi lạ

## Backlog ưu tiên gần nhất
1. Metadata-aware memory search
2. `/api/memory/health`
3. Memory dedupe + TTL
4. Snake stage state machine (config-driven)
5. Scout/Builder/Guard agent profile draft

## KPI đề xuất
- p95 memory search < 50ms (local run)
- feedback good ratio > 80%
- fallback-to-local rate < 5%
- task completion without retry > 90%
