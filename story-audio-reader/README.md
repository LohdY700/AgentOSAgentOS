# Story Audio Reader

App đọc truyện bằng giọng trình duyệt (Web Speech API).

## Chạy nhanh

```bash
cd story-audio-reader
python3 -m http.server 8099
```

Mở: http://127.0.0.1:8099

## Tính năng
- Dán nội dung truyện và đọc thành tiếng
- OCR từ ảnh (jpg/png) để trích chữ rồi đọc luôn
- Chọn giọng đọc (ưu tiên tiếng Việt nếu có)
- Điều chỉnh tốc độ
- Tạm dừng / tiếp tục / dừng
- Tự chia đoạn theo xuống dòng để đọc mượt hơn

> Ghi chú: OCR dùng `tesseract.js` CDN, cần có internet khi tải engine lần đầu.
