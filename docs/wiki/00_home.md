---
title: "Home — Second Brain của dự án ErpNext_Hermes"
type: index
status: current
created: 2026-07-24
updated: 2026-07-24
---

# Second Brain — ErpNext_Hermes

Đây không phải tài liệu hướng dẫn (đã có `PROJECT_HANDBOOK.md`, `docs/PLANNING.md`,
`docs/OPERATIONS.md`). Đây là **bộ nhớ ngoài** cho bất kỳ agent AI nào (Claude,
Hermes, Antigravity...) làm việc trên dự án này — nơi lưu lại những sự thật,
quyết định, và bài học tốn công phát hiện, để **không phải tìm lại/suy luận lại
từ đầu** mỗi phiên làm việc mới.

## Nguyên tắc thiết kế (5 nguyên lý, áp dụng cho vault này)

1. **Ánh xạ theo kiến trúc thật** — cây thư mục gốc mô phỏng đúng các thành
   phần thật của hệ thống (kiến trúc / quyết định / sự cố / vận hành), không
   phải chủ đề tùy hứng.
2. **Tách vòng đời** — `99_archive/` chứa hiểu biết đã bị thay thế (ví dụ:
   "Hermes chạy Docker" — sai, đã archive). Các thư mục còn lại là
   **SSOT** (đang đúng tại thời điểm `updated`). Không có thư mục `_wip/`
   riêng — ghi chú đang dở dang thì để `status: draft` trong frontmatter.
3. **Phẳng, tối đa 3 cấp** — `docs/wiki/<NN_loại>/<note>.md`, không lồng sâu
   hơn. Nếu một thư mục phình to, dùng frontmatter (`related`, `tags`) để
   phân loại thêm, không tạo thư mục con.
4. **Máy đọc được** — tên file `snake_case`, tiền tố số (`01_`, `02_`...) để
   tự kiểm soát thứ tự. Mọi ngữ cảnh (ai viết, khi nào, liên quan gì) nằm
   trong YAML frontmatter, không nhét vào tên file.
5. **Phá vỡ là một quy trình** — không sửa đè lịch sử. Khi 1 note bị thay
   thế: đổi `status: superseded`, thêm `superseded_by: [[note-moi]]`, chuyển
   xuống `99_archive/`, và ghi 1 dòng vào `CHANGELOG.md` nếu đó là thay đổi
   kiến trúc thật (không chỉ note nội bộ).

## Cây thư mục

- [`01_architecture/`](01_architecture/) — hệ thống được xây dựng ra sao
  (sự thật ổn định: ERPNext Bridge, Hermes bare-metal, mạng Caddy...).
- [`02_decisions/`](02_decisions/) — tại sao chọn X thay vì Y (ADR ngắn).
- [`03_incidents/`](03_incidents/) — bug thật đã gặp + nguyên nhân gốc + cách
  sửa. **Đây là phần giá trị nhất của vault** — mỗi incident tốn hàng chục
  bước điều tra để tìm ra, ghi lại 1 lần để agent sau không lặp lại.
- [`04_operations/`](04_operations/) — cách vận hành hằng ngày (không secret
  thật, chỉ pointer tới nơi lưu secret).
- [`05_glossary/`](05_glossary/) — từ vựng riêng của dự án (profile, bridge,
  HERMES_HOME, L0-L3...) để agent mới không hiểu nhầm.
- `99_archive/` — hiểu biết cũ đã bị thay thế, giữ lại để biết *tại sao* đã
  đổi (không xoá lịch sử).

## Quan hệ với các tài liệu khác

- `PROJECT_HANDBOOK.md` vẫn là tài liệu tổng, đọc đầy đủ khi mới nhận việc.
- Vault này là lớp **bổ sung**, không thay thế: các note ở đây ngắn, atomic,
  có frontmatter để tìm nhanh — dùng khi cần tra 1 sự thật cụ thể mà không
  muốn đọc lại 600 dòng handbook.
- Không copy nguyên văn nội dung từ handbook/CHANGELOG vào đây — mỗi note có
  `source:` trỏ về đúng chỗ, tránh 2 nguồn sự thật lệch nhau theo thời gian.

## Đồng bộ vault

Vault này tồn tại ở 2 nơi:

- `docs/wiki/` trong repo Git (bản chính, version-controlled) — bạn đang đọc.
- `/root/wiki` trên VPS 173.249.51.69 (bản Hermes agent thực sự đọc/ghi khi
  chat qua Telegram/dashboard, dùng skill Obsidian có sẵn).

**Chưa có cơ chế tự động đồng bộ 2 bản này** (ghi rõ để không ai lầm tưởng).
Quy trình hiện tại: khi Hermes tạo/sửa note trên VPS qua chat, người vận hành
cần copy thủ công về repo và commit. Xem
[`04_operations/wiki_sync_process.md`](04_operations/wiki_sync_process.md).
