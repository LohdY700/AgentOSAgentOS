# Continual Learning 7-Day Blueprint (AIOS)

## Priority order
Traces -> Context/Memory -> Skills -> Harness -> Model

## Day 1: Tracing
- Gắn trace cho mọi phiên chạy.
- Metadata bắt buộc: `thread_id`, `user_id`, `task_type`, `agent_version`, `tool_calls`, `latency_ms`.

## Day 2: 3-scope Memory
- User memory: `memories/users/{user_id}/...`
- Agent memory: `memories/agent/...`
- Org memory/policies: `policies/...` (read-only)

## Day 3: Memory write rules
- Chỉ lưu thứ bền vững và hữu ích cho lần sau.
- Tách rõ `facts`, `preferences`, `skills`.

## Day 4: Sensitive guardrails
- Policy/compliance luôn read-only.
- Shared memory không cho user ghi trực tiếp.
- Ghi nhạy cảm cần approval.

## Day 5: Skills learning
- Chọn 5 tác vụ lặp nhiều nhất.
- Mỗi tác vụ tạo 1 file skill markdown.

## Day 6: Failure-mode review từ traces
- Sai tool, sai flow, thiếu verify, token cao, chậm.

## Day 7: Harness updates
- Sửa system prompt
- thêm verify step
- thêm guardrails
- thêm logic stop/ask/escalate

## Anti-patterns
1) Fine-tune quá sớm.
2) Không tách scope memory.
3) Cho agent sửa policy.
4) Chỉ lưu facts mà không lưu skills.
5) Không trace nhưng vẫn nói tối ưu.
