---
title: "Quyết định: Hermes chạy bare-metal + systemd, không Docker"
type: decision
status: current
created: 2026-07-24
updated: 2026-07-24
source: "PROJECT_HANDBOOK.md mục 4; commit 7ced13e"
related: ["[[../01_architecture/hermes_bare_metal]]"]
tags: [architecture, hermes, deploy]
---

# Quyết định: Hermes chạy bare-metal + systemd, không Docker

## Bối cảnh

Ansible role gốc giả định Hermes chạy qua Docker Compose (`compose.yaml.j2`,
biến `hermes_image`). Khi đối chiếu với VPS thật (2026-07-16), phát hiện
thực tế hoàn toàn khác: không có image `hermes-agent` nào trong `docker
images`, các tiến trình thật là
`/usr/local/lib/hermes-agent/venv/bin/python -m hermes_cli.main --profile
<name> gateway run` chạy trực tiếp trên host.

## Quyết định

Viết lại toàn bộ role `hermes` để khớp với thực tế bare-metal: mỗi profile
1 systemd unit riêng (`hermes-gateway-<profile>.service`), xoá
`compose.yaml.j2` và biến `hermes_image`.

## Lý do

- Repo phải mô tả đúng thực tế đang chạy, không phải kiến trúc dự định ban
  đầu nhưng chưa từng triển khai — "giả kiến trúc" gây hiểu lầm nghiêm trọng
  cho agent/dev sau.
- Cài đặt Hermes chính nó (venv, `hermes --version` báo có "+1 carried
  commit" cục bộ chưa rõ nội dung) **không** được tự động hoá trong role —
  coi là tiền đề thủ công, tránh rủi ro ghi đè bản vá cục bộ không rõ.

## Hệ quả

- `roles/hermes/templates/hermes-gateway.service.j2` cần flag `--replace`
  trong `ExecStart` (xem [[../03_incidents]] nếu có note riêng — nếu chưa có,
  ghi nhớ: thiếu `--replace` gây restart-loop vì `gateway.pid`/`gateway.lock`
  cũ chưa kịp giải phóng).
- Mọi role liên quan (Caddy, firewall) phải tính tới việc Hermes là tiến
  trình host, không phải container — ảnh hưởng trực tiếp tới cách network
  routing hoạt động (xem
  [[0002_caddy_https_not_ip_whitelist]]).
