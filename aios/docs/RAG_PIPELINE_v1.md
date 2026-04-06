# AIOS — RAG Pipeline v1

## Mục tiêu
Chuẩn hóa cách Su và đội nhỏ dùng RAG để trả lời đúng dữ liệu, đúng ngữ cảnh, giảm hallucination.

## 1) Pipeline tổng quan
1. **Ingest**: nhận dữ liệu mới (docs, mission notes, memory items)
2. **Chunk/Store**: lưu theo backend (langchain/local) + metadata
3. **Retrieve**: truy hồi theo query + filter metadata (`kind`, `role`, `time-range`)
4. **Rank**: ưu tiên nguồn mới nhất và phù hợp nhất
5. **Generate**: tạo trả lời ngắn gọn, action-first
6. **Post-Update**: ghi nhận quyết định/tiến độ vào Mission Control

## 2) Nguồn dữ liệu ưu tiên (retrieval order)
1. `aios/data/mission-control.json` (trạng thái công việc mới nhất)
2. `memory/YYYY-MM-DD.md` (nhật ký gần nhất)
3. `aios/docs/HANDOFF_*.md`, release notes, behavior specs
4. memory backend semantic search (langchain/local fallback)

## 3) Metadata schema đề xuất
- `kind`: `task|decision|preference|note|incident|release`
- `role`: `owner|assistant|subagent`
- `source`: `mission-control|memory-file|docs|api`
- `created_at`: ISO datetime (Asia/Bangkok)
- `tags`: list string

## 4) Query strategy (v1)
- Query chính: câu hỏi user
- Query mở rộng: synonym ngắn (VD: "tiến độ" -> "status", "in_progress")
- Top-k mặc định: 5
- Filter ưu tiên:
  - nếu hỏi tiến độ => `kind in [task,note,decision]`
  - nếu hỏi hành vi => `kind in [preference,decision]`

## 5) Generation rules (gắn với style Su)
- Trả lời ngắn gọn, có kết luận trước.
- Nêu 1–3 bullet bằng chứng/trạng thái.
- Nếu thiếu dữ liệu: nói rõ "chưa có dữ liệu" + đề xuất bước lấy dữ liệu.

## 6) Chỉ số theo dõi
- Retrieval hit-rate
- p95 search latency
- Feedback good/bad ratio
- Fallback-to-local rate

## 7) Rollout plan
### Phase A (ngay)
- Áp dụng retrieval order + generation rules cho Su.
- Cập nhật Mission Control sau mỗi thay đổi quan trọng.

### Phase B (tiếp theo)
- Thêm filter metadata thật vào `/api/memory/search`.
- Thêm `/api/memory/health` + card dashboard.

### Phase C
- Bổ sung rerank và policy scoring nhẹ.

## 8) Done criteria cho RAG v1
- Có tài liệu pipeline + schema rõ.
- Có ít nhất 1 endpoint hỗ trợ filter metadata.
- Có theo dõi latency và health trên dashboard.
