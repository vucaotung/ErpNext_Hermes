---
title: "Từ vựng riêng của dự án ErpNext_Hermes"
type: glossary
status: current
created: 2026-07-24
updated: 2026-07-24
source: "PROJECT_HANDBOOK.md"
tags: [glossary]
---

# Từ vựng riêng của dự án ErpNext_Hermes

- **Profile** — 1 "nhân cách"/bot Hermes độc lập (`ops-admin`, `staff-work`,
  `sales-crm`, `system-maintainer`), mỗi profile có bot token + ERPNext API
  user + bridge shared secret riêng. Không phải "user".
- **Bridge** — viết tắt quen dùng cho ERPNext API Bridge
  (`integration/erpnext-bridge`), lớp duy nhất được gọi ERPNext.
- **HERMES_HOME** — biến môi trường xác định state directory của 1 profile
  (`~/.hermes/profiles/<name>`). Set sai/thiếu → dữ liệu ghi nhầm profile
  mặc định (xem cảnh báo `[HERMES_HOME fallback]` trong log nếu gặp).
- **L0–L3** — phân cấp quyền trong `hermes_ops`: L0 = hệ thống/admin kỹ
  thuật, L1 = Director, L2 = Team Lead, L3 = Staff. Xem
  `PROJECT_HANDBOOK.md` mục 7.
- **`/link`** — lệnh Telegram gắn danh tính người dùng thật với Telegram ID,
  xử lý ở tầng gateway hook, không qua LLM.
- **Second Brain / vault** — chính là `docs/wiki/` bạn đang đọc — bộ nhớ
  ngoài cho agent, không phải tài liệu hướng dẫn người dùng.
- **SSOT** — Single Source of Truth. Trong vault này: mọi thư mục trừ
  `99_archive/` được coi là SSOT tại thời điểm `updated` trong frontmatter.
