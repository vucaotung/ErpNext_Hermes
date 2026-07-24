---
title: "Quyết định: Dashboard Hermes qua Caddy HTTPS + fail2ban, không whitelist IP"
type: decision
status: current
created: 2026-07-24
updated: 2026-07-24
source: "CHANGELOG.md [2026-07-24]; commit d64a066"
related:
  - "[[../03_incidents/2026-07-24_ip_whitelist_locked_out_admin_on_travel]]"
  - "[[../01_architecture/caddy_networking]]"
tags: [architecture, security, dashboard]
---

# Quyết định: Dashboard Hermes qua Caddy HTTPS + fail2ban, không whitelist IP

## Bối cảnh

Xem incident
[[../03_incidents/2026-07-24_ip_whitelist_locked_out_admin_on_travel]] —
admin bị khoá khỏi dashboard mỗi khi đổi IP (đi công tác, đổi mạng).

## Các phương án cân nhắc

1. **Giữ whitelist IP, thêm rule mỗi lần đổi** — không bền, cần thao tác tay
   liên tục, và có độ trễ (admin bị khoá tới khi ai đó sửa firewall).
2. **VPN riêng (WireGuard)** — an toàn hơn (dashboard không lộ ra Internet)
   nhưng cần cài + bật VPN client mỗi lần dùng trên mọi thiết bị — phiền cho
   nhu cầu truy cập nhanh khi di chuyển.
3. **Domain HTTPS qua Caddy + fail2ban** (đã chọn) — mở qua trình duyệt bất
   kỳ, không cần cài gì thêm, bảo vệ bằng TLS thật + chặn brute-force IP.

## Quyết định

Chọn phương án 3. Được hỏi trực tiếp Tùng, chọn "Mở qua domain HTTPS +
fail2ban" so với VPN.

## Chi tiết kỹ thuật quan trọng

- Dashboard (`hermes-serve`, cổng 9119) **không** đổi sang bind loopback
  đơn thuần — vẫn bind `0.0.0.0` vì Caddy (chạy trong container Docker
  `proxy-net`) cần "hairpin" vào host để reverse-proxy.
- `host.docker.internal`/`host-gateway` **không dùng được** trên host này —
  nó resolve vào bridge Docker mặc định (`docker0`, 172.17.0.1), không phải
  `proxy-net` (172.19.0.1) nơi container Caddy thực sự chạy. Phải hardcode
  gateway IP đúng mạng (`caddy_proxy_network_gateway: 172.19.0.1` trong
  `group_vars/all.yml`).
- UFW: xoá hết rule public/whitelist-theo-IP cho cổng 9119, thay bằng 1 rule
  duy nhất chỉ cho phép subnet nội bộ `172.19.0.0/16` (mạng Caddy) — cổng
  9119 không còn truy cập được trực tiếp từ Internet, chỉ qua Caddy ở 443.
- fail2ban đọc log JSON access log riêng của Caddy cho site dashboard (không
  phải log của `hermes-serve` — tiến trình đó không tự ghi IP client ra
  file), ban IP sau 5 lần đăng nhập sai (401/403 vào
  `/auth/password-login`) trong 10 phút.

## Hệ quả

Nếu `proxy-net` bị xoá/tạo lại với subnet khác, `caddy_proxy_network_gateway`
phải cập nhật tay — không có auto-discovery. Ghi rõ trong comment của
`group_vars/all.yml`.
