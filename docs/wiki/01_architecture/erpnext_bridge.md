---
title: "Kiến trúc: ERPNext API Bridge — lớp duy nhất được gọi ERPNext"
type: architecture
status: current
created: 2026-07-24
updated: 2026-07-24
source: "README.md; docs/PLANNING.md; PROJECT_HANDBOOK.md mục 7"
related: ["[[../03_incidents/2026-07-24_bridge_base_url_docker_hostname_unreachable]]"]
tags: [architecture, bridge, security]
---

# Kiến trúc: ERPNext API Bridge — lớp duy nhất được gọi ERPNext

## Nguyên tắc bất biến (không được vi phạm)

- Hermes **không bao giờ** gọi ERPNext REST API trực tiếp hay MariaDB trực
  tiếp. Mọi thao tác đi qua `integration/erpnext-bridge` (FastAPI nội bộ).
- Whitelist tool cứng trong
  `integration/erpnext-bridge/app/tools/registry.py`. `FORBIDDEN_TOOL_NAMES`
  (`erp_execute_sql`, `erp_call_any_endpoint`...) không được tồn tại trong
  code — có test tự động khẳng định điều này (không phải quy ước bằng lời).
- Idempotency key bắt buộc cho mọi write, audit log không log secret, rate
  limit theo profile.

## Vị trí mạng

- Container publish `127.0.0.1:8642` (loopback host) — **không** publish ra
  0.0.0.0. Đây là lý do Hermes bare-metal phải gọi `127.0.0.1:8642`, không
  phải tên service Docker `erpnext-bridge`. Xem incident đã gặp thật:
  [[../03_incidents/2026-07-24_bridge_base_url_docker_hostname_unreachable]].

## Danh tính người dùng Telegram

Không bao giờ để LLM tự khai báo danh tính. Gắn danh tính qua lệnh `/link`
xử lý ở **tầng gateway hook** (`command:link`), không qua LLM, không thể giả
mạo. Xem `PROJECT_HANDBOOK.md` mục 7 để có mô hình phân quyền L0-L3 đầy đủ.
