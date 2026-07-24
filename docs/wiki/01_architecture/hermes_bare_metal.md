---
title: "Kiến trúc: Hermes chạy bare-metal, không Docker"
type: architecture
status: current
created: 2026-07-24
updated: 2026-07-24
source: "PROJECT_HANDBOOK.md mục 4; group_vars/all.yml"
related: ["[[../02_decisions/0001_bare_metal_not_docker]]"]
tags: [architecture, hermes]
---

# Kiến trúc: Hermes chạy bare-metal, không Docker

## Sự thật cốt lõi

- Cài đặt tại `/usr/local/lib/hermes-agent`, venv Python tại
  `/usr/local/lib/hermes-agent/venv`.
- Mỗi profile (`ops-admin`, `staff-work`, `sales-crm` [tắt],
  `system-maintainer` [tắt]) là **1 tiến trình riêng**:
  `python -m hermes_cli.main --profile <name> gateway run --replace`,
  quản lý bởi systemd unit `hermes-gateway-<name>.service`.
- `HERMES_HOME` set qua `Environment=` trong systemd unit, trỏ
  `/root/.hermes/profiles/<name>` — **không bao giờ** dùng `~/.hermes/` global
  cho plugin/hook/script riêng profile.
- Dashboard (`hermes serve`/`hermes dashboard`, xem
  [[../03_incidents/2026-07-24_hermes_serve_vs_dashboard_no_web_ui]]) là
  **1 tiến trình chung** cho mọi profile, không nằm trong vòng lặp
  `hermes_profiles`, unit riêng `hermes-serve.service`, cổng 9119.
- Cài đặt Hermes chính nó (`hermes --version` báo "+1 carried commit" cục
  bộ) là tiền đề thủ công, **không** tự động hoá qua Ansible — role
  `hermes` chỉ quản lý config/systemd, không cài/update binary.

## Vì sao cần biết

Bất kỳ ai nhìn `roles/hermes/templates/` mà không đọc note này dễ nhầm rằng
đây là hệ thống Docker (do có `compose.yaml.j2` cũ từng tồn tại, đã xoá).
Xem lý do đầy đủ ở
[[../02_decisions/0001_bare_metal_not_docker]].
