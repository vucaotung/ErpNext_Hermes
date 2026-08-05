---
title: "Kiến trúc: Onyx Ingest Bridge — nạp URL vào kho tri thức Onyx qua Hermes"
type: architecture
status: current
created: 2026-08-01
updated: 2026-08-01
source: "CHANGELOG.md [2026-08-01]; integration/onyx-bridge/"
related: ["[[erpnext_bridge]]"]
tags: [architecture, bridge, onyx, security]
---

# Kiến trúc: Onyx Ingest Bridge

## Nguyên tắc bất biến

- Đây là service **riêng biệt hoàn toàn** với `integration/erpnext-bridge`.
  Onyx Ingest Bridge không đọc được ERPNext; ERPNext Bridge không ra được
  Internet. Không gộp chung để giữ đúng nguyên tắc mỗi bridge một phạm vi
  hẹp, whitelist-only.
- Chỉ làm đúng 1 việc: nhận `{url, target}`, fetch trang, trích văn bản,
  đẩy vào Onyx Ingestion API (`/api/onyx-api/ingestion`) theo đúng
  Document Set (`target: legal -> cc_pair_id`, `project -> cc_pair_id`
  khác — xem `app/config.py`).
- Chặn SSRF: chỉ `http`/`https`, chặn IP private/loopback/link-local/
  reserved/multicast (`app/fetch.py`).
- Không thực thi bất cứ thứ gì tìm thấy trên trang đã fetch.
- Xác thực per-profile giống hệt erpnext-bridge: mỗi Hermes profile có
  1 shared secret riêng, không có master token (`app/auth.py`).

## Đường đi của một lệnh /ingest

1. User gửi `/ingest <url> [legal|project]` qua Telegram.
2. Gateway hook `roles/hermes/files/profiles/ops-admin/hooks/ingest-command/`
   nhận event `command:ingest` — có `user_id` Telegram **thật** từ gateway
   (không phải LLM tự suy ra, không giả mạo được). Plugin
   `.../plugins/onyx-ingest/` chỉ có nhiệm vụ đăng ký command này là
   "known" để hook có thể fire.
3. Hook gọi `POST http://127.0.0.1:8643/ingest_url` trên chính host Onyx
   (bare-metal venv, xem `integration/onyx-bridge/onyx-bridge.service`,
   không chạy Docker — khác erpnext-bridge).
4. Bridge fetch + trích text + đẩy Onyx, trả về title/document_id/
   already_existed, ghi audit log (không log API key, không log toàn văn
   tài liệu).
5. Hook trả lời user trên Telegram kèm tên tài liệu + Document Set đã nạp.

## Quyết định đã cân nhắc nhưng không chọn

Free-form LLM tool (SKILL.md để agent tự phân loại legal/project rồi tự
gọi API) — không chọn. Mọi lệnh Telegram nhạy cảm khác (`/link`, `/assign`)
đều dùng gateway hook xác định, không phải LLM tool, vì lý do bảo mật danh
tính (`user_id` không thể giả mạo qua hook, nhưng có thể bị LLM hiểu sai
qua tool call). `/ingest` theo đúng pattern đó để nhất quán.

## Cấu hình

- `roles/hermes/templates/profile.env.j2` — biến `ONYX_BRIDGE_BASE_URL`,
  `ONYX_BRIDGE_TOKEN`, guard theo `item.onyx_ingest_enabled`.
- `inventories/production/group_vars/all.yml` — profile `ops-admin` có
  `onyx_ingest_enabled: true` và `onyx-ingest` trong danh sách `plugins`.
- Secret thật (`vault_onyx_bridge_shared_secret_ops_admin`,
  `ONYX_API_KEY` trong `integration/onyx-bridge/.env` trên VPS) không nằm
  trong repo — xem `integration/onyx-bridge/env.template` cho danh sách
  biến cần điền khi deploy.

## Chưa tự động hoá

- Chưa có Ansible role/task để tự deploy `integration/onyx-bridge` (venv,
  systemd unit) — hiện làm tay qua SSH, giống cách erpnext-bridge từng bắt
  đầu. Nên thêm 1 role `onyx-bridge` tương tự `roles/erpnext-bridge` khi
  có thời gian.
- `hermes plugins enable onyx-ingest` cũng chưa tự động — làm tay 1 lần
  trên VPS, danh sách `plugins:` trong inventory hiện chỉ là tài liệu ý
  định, chưa có task Ansible đọc nó để tự bật.
