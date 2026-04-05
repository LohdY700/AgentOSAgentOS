# Launch Post (VN)

Mình vừa hoàn thành **AIOS v0.1.0** — một thử nghiệm hệ điều hành **AI-native**:

- ISO ~65MB
- Boot ~5 giây
- Event-first runtime (push events thay vì polling)
- Guard có 2 mode: `learning -> strict`

Ở phase này, mình tập trung vào nền tảng runtime:
- Event envelope chuẩn
- Event bus có retry + dead-letter + idempotency cơ bản
- Process guard để phát hiện process lạ
- Benchmark + report pipeline + CI

Repo hiện có đầy đủ:
- Demo script 2 phút
- Architecture doc
- Known limitations (nói thẳng các giới hạn hiện tại)
- Release checklist

Đây mới là bước khởi đầu, nhưng hướng đi mình tin là đúng: **AI agents nên sống trong môi trường được thiết kế cho chúng từ gốc**.

#AIOS #BuildInPublic #AIAgent #Linux #Buildroot
