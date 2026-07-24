---
title: "UFW chặn theo IP admin cụ thể khoá luôn admin khi đổi mạng"
type: incident
status: superseded
superseded_by: "[[../02_decisions/0002_caddy_https_not_ip_whitelist]]"
created: 2026-07-24
updated: 2026-07-24
source: "CHANGELOG.md [2026-07-24]; commit d64a066"
tags: [firewall, dashboard, access]
---

# UFW chặn theo IP admin cụ thể khoá luôn admin khi đổi mạng

## Hiện tượng

Tùng báo "không truy cập được vào hermes desktop" (dashboard cổng 9119).

## Nguyên nhân gốc

`ufw` chỉ cho phép đúng 1 IP admin cố định truy cập cổng 9119
(`116.96.46.128`). IP thực tế của Tùng đã đổi (`116.96.47.160`, nhà mạng gán
IP động). Log kernel (`journalctl -k | grep DPT=9119`) cho thấy hàng loạt
gói **UFW BLOCK** từ IP mới đúng lúc Tùng báo lỗi — xác nhận trực tiếp,
không cần đoán.

## Cách khắc phục tạm (ngay lúc đó)

`ufw allow from <IP mới> to any port 9119` — vá nhanh nhưng không giải quyết
gốc (IP sẽ đổi tiếp khi đi công tác).

## Giải pháp thật (superseded — xem quyết định liên quan)

Bỏ hẳn cơ chế whitelist-theo-IP, chuyển sang Caddy HTTPS reverse-proxy +
fail2ban. Xem
[[../02_decisions/0002_caddy_https_not_ip_whitelist|quyết định 0002]].

## Hệ quả cho agent tương lai

Không dùng UFW whitelist-theo-IP cho bất kỳ dịch vụ nào admin cần truy cập
khi di chuyển — đây là anti-pattern đã được thay thế trong dự án này.
