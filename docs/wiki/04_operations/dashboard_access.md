---
title: "Vận hành: truy cập dashboard Hermes"
type: operations
status: current
created: 2026-07-24
updated: 2026-07-24
source: "CHANGELOG.md [2026-07-24]"
related:
  - "[[../02_decisions/0002_caddy_https_not_ip_whitelist]]"
  - "[[../03_incidents/2026-07-24_hermes_serve_vs_dashboard_no_web_ui]]"
tags: [operations, dashboard]
---

# Vận hành: truy cập dashboard Hermes

- URL: `https://hermes.enterpriseos.bond/login` (không dùng `/` — trang chủ
  redirect qua endpoint OAuth gây lỗi 500 với auth kiểu password, xem
  [[../03_incidents/2026-07-24_hermes_serve_vs_dashboard_no_web_ui]] nếu cần
  chi tiết kỹ thuật).
- Username: `admin`. Mật khẩu do Tùng quản lý (lưu dạng hash scrypt trong
  `/root/.hermes/config.yaml`, không đọc lại được — nếu quên, cần đặt lại
  bằng `plugins.dashboard_auth.basic.hash_password()`, không phải sửa tay
  hash).
- Không cần VPN/cấu hình đặc biệt khi di chuyển — chỉ cần trình duyệt bất
  kỳ. fail2ban tự ban IP sau 5 lần đăng nhập sai/10 phút.
- Nếu không truy cập được: kiểm tra `systemctl status hermes-serve.service`
  và `docker ps --filter name=company-caddy` trên VPS trước, KHÔNG giả định
  lại là vấn đề firewall theo IP (đã bỏ cơ chế đó).
