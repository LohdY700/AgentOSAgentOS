# AIOS — Small Team Workplan v1

## Team Structure

### 1) Su (Lead / Orchestrator)
- Nhận mục tiêu từ sếp
- Chia task, giao đúng agent
- Review chất lượng + merge + báo cáo

### 2) Behavior Trainer Agent
- Train hành vi nói chuyện
- Duy trì spec/dataset/rubric
- Daily refine từ feedback thực tế

### 3) Memory/Core Agent
- Phát triển memory engine
- Theo dõi benchmark + CI gate + doctor
- Tối ưu performance/reliability

### 4) Dashboard/API Agent
- Nâng cấp API + dashboard hiển thị health
- Viết integration tests

### 5) Docs/Release Agent
- Release notes/changelog/demo scripts
- Launch posts + tài liệu vận hành

---

## Working Model

- Mỗi ngày chạy 1 sprint ngắn (Sáng/Trưa/Cuối ngày)
- Mỗi lane tối đa 1 nhiệm vụ active để tránh tràn context
- Cuối ngày: test tổng + handoff + next-day plan

---

## Sprint hiện tại (Kickoff)

### Lane A — Behavior
- [ ] Gắn rubric vào vòng feedback hằng ngày
- [ ] Tạo form chấm nhanh 5 tiêu chí

### Lane B — Memory/Core
- [ ] Thêm metadata-aware memory search (kind/role/time-range)
- [ ] Thêm endpoint `/api/memory/health`

### Lane C — Dashboard/API
- [ ] Hiển thị memory health + latency card
- [ ] Thêm integration test cho filter search

### Lane D — Docs/Release
- [ ] Cập nhật docs theo metadata-aware search
- [ ] Chuẩn hóa playbook troubleshooting memory

---

## Done Criteria (Definition of Done)

Một task được xem là DONE khi đủ:
1) Code/docs hoàn chỉnh
2) Test pass (local + CI liên quan)
3) Changelog/release note cập nhật nếu cần
4) Có tóm tắt ngắn “impact” cho sếp
