---
title: "BRIDGE_BASE_URL trỏ hostname Docker, không resolve được từ Hermes bare-metal"
type: incident
status: current
created: 2026-07-24
updated: 2026-07-24
source: "CHANGELOG.md [2026-07-16]; PROJECT_HANDBOOK.md mục 4"
related: ["[[../01_architecture/hermes_bare_metal]]", "[[../01_architecture/erpnext_bridge]]"]
tags: [networking, docker, bridge]
---

# BRIDGE_BASE_URL trỏ hostname Docker, không resolve được từ Hermes bare-metal

## Hiện tượng

`/link`, `/mytasks`, `/assign` (mọi lệnh Telegram cần gọi ERPNext API Bridge)
fail âm thầm.

## Nguyên nhân gốc

`.env` của cả 2 profile (`ops-admin`, `staff-work`) có
`BRIDGE_BASE_URL=http://erpnext-bridge:8642` — đây là tên service trong
Docker Compose network, **chỉ resolve được từ trong container khác cùng
network**. Hermes chạy bare-metal trên host (không phải container), nên
hostname này không resolve được từ host — trong khi ERPNext Bridge publish
cổng ra `127.0.0.1:8642` (loopback host thật).

## Cách phát hiện

`curl http://erpnext-bridge:8642/healthz` từ host → lỗi resolve/connect.
`curl http://127.0.0.1:8642/healthz` từ host → thành công. So sánh 2 kết
quả này xác định ngay vấn đề là DNS/network scope, không phải bridge chết.

## Cách khắc phục

Sửa `BRIDGE_BASE_URL=http://127.0.0.1:8642` cả live (`sed -i` trên 2 file
`.env`) và trong template Ansible (`roles/hermes/templates/profile.env.j2`).

## Hệ quả cho agent tương lai

Bất kỳ biến trỏ tới `erpnext-bridge`/`erpnext-frontend`/tên service Docker
nào khác, nếu được dùng bởi tiến trình bare-metal (Hermes) — đó là bug. Chỉ
container khác trong `proxy-net`/network Docker mới được dùng tên service;
mọi thứ chạy trên host phải dùng `127.0.0.1:<port>` (yêu cầu port đó có
publish ra loopback trong compose).
