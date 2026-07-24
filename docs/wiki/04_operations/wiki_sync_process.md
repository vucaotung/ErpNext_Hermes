---
title: "Vận hành: đồng bộ vault Second Brain (repo ↔ VPS)"
type: operations
status: current
created: 2026-07-24
updated: 2026-07-24
source: "docs/wiki/00_home.md"
tags: [operations, wiki, second-brain]
---

# Vận hành: đồng bộ vault Second Brain (repo ↔ VPS)

## Hiện trạng (chưa tự động)

Vault tồn tại ở 2 nơi:

1. `docs/wiki/` trong repo Git — bản version-controlled, chỉnh sửa qua
   Claude/Cowork hoặc trực tiếp trên máy.
2. `/root/wiki` trên VPS — bản Hermes agent thực sự đọc/ghi khi chat qua
   Telegram/dashboard (dùng skill Obsidian có sẵn, đọc biến môi trường
   `OBSIDIAN_VAULT_PATH`).

**Không có cron/rclone tự động đồng bộ 2 bản này.** Đây là khoảng trống đã
biết, tương tự off-site backup chưa cấu hình — không giả vờ là đã xong.

## Quy trình thủ công hiện tại

- Khi **Claude/Cowork** sửa vault (qua Desktop): sau khi xong, đồng bộ sang
  VPS bằng SFTP/rsync (`/root/wiki`), rồi restart không cần thiết (chỉ là
  file, Hermes đọc trực tiếp mỗi lần dùng skill Obsidian).
- Khi **Hermes** (qua Telegram) tạo/sửa note trên VPS: người vận hành cần
  tự copy về repo và commit — hiện chưa có nhắc nhở tự động, dễ quên.

## Cải tiến đề xuất (chưa làm — xem GitHub Issues)

- Cron đơn giản: `rsync` 2 chiều theo giờ, cảnh báo qua Telegram nếu có
  xung đột (2 bản cùng sửa 1 file).
- Hoặc: bỏ bản trên VPS, thay bằng Hermes clone thẳng repo Git (cần deploy
  key riêng, quyền ghi hạn chế chỉ vào `docs/wiki/`) — phức tạp hơn nhưng
  loại bỏ hoàn toàn 2-nguồn-sự-thật.
