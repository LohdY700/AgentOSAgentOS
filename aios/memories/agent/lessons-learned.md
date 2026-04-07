# Agent Lessons Learned

- Đừng preload nặng khi startup dashboard nếu dễ làm process bị kill.
- Mission Control cần cache-busting frontend để tránh UI kẹt ở bản cũ.
- Dữ liệu báo cáo cần auto-backup + auto-restore để tránh cảm giác "mất dữ liệu".
