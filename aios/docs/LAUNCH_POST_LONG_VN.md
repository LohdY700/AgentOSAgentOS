# Launch Post dài (VN)

Mình vừa hoàn thành **AIOS v0.1.0** — một thử nghiệm xây runtime/hệ điều hành theo hướng **AI-native**.

Thay vì coi AI là “plugin thêm vào sau”, mình muốn thử cách ngược lại: thiết kế môi trường chạy để AI agents có thể hoạt động tự nhiên ngay từ đầu.

## Ở bản v0.1.0 có gì?
- ISO ~65MB
- Boot ~5 giây
- Event-first runtime (ưu tiên push events thay vì polling)
- Process guard có 2 mode:
  - `learning` để quan sát và học baseline
  - `strict` để cảnh báo process lạ

## Nền tảng kỹ thuật phase 1
- Canonical event envelope
- Event bus in-memory có retry + dead-letter + idempotency cơ bản
- Benchmark/report pipeline
- Unit tests cho các luồng reliability chính
- CI để giữ nhịp chất lượng khi iterate

## Vì sao mình thích hướng này?
Với agent systems, polling liên tục rất nhanh đụng trần (latency, cost, complexity). Event-first làm luồng phản ứng tự nhiên hơn, đỡ lãng phí hơn, và nhìn rõ state transitions hơn.

AIOS vẫn còn sớm, nhưng mình ưu tiên:
1) chạy được,
2) đo được,
3) giải thích được,
4) cải tiến được.

Nếu bạn đang làm về agent infra/edge runtime/embedded AI, mình rất muốn trao đổi thêm.

#AIOS #BuildInPublic #AIAgent #Linux #Buildroot
