---
title: "Kiến trúc: mạng Caddy — container gọi ngược vào host"
type: architecture
status: current
created: 2026-07-24
updated: 2026-07-24
source: "group_vars/all.yml comment; roles/caddy/"
related: ["[[../02_decisions/0002_caddy_https_not_ip_whitelist]]"]
tags: [architecture, networking, caddy, docker]
---

# Kiến trúc: mạng Caddy — container gọi ngược vào host

## Sơ đồ thực tế

```
Internet (443) → company-caddy (container, mạng Docker proxy-net, 172.19.0.0/16)
                    ├─ erp.enterpriseos.bond   → erpnext-frontend:8080 (cùng mạng Docker, tên service resolve OK)
                    └─ hermes.enterpriseos.bond → 172.19.0.1:9119 (gateway IP của proxy-net, "hairpin" ra host)
```

## Điểm dễ nhầm nhất

`erp.enterpriseos.bond` dùng **tên service Docker** (`erpnext-frontend`) vì
đích là container khác cùng mạng `proxy-net`. Nhưng
`hermes.enterpriseos.bond` KHÔNG thể làm vậy vì Hermes chạy **bare-metal
trên host**, không phải container — Caddy phải gọi ngược ra IP gateway của
chính mạng nó đang chạy.

`host.docker.internal` (alias `host-gateway` chuẩn của Docker) **không dùng
được** ở đây: nó resolve vào bridge Docker **mặc định** (`docker0`,
172.17.0.1), trong khi `company-caddy` thực tế chạy trong mạng
**`proxy-net`** (172.19.0.1) — 2 mạng Docker khác nhau, gateway khác nhau.
Đã kiểm chứng bằng `docker exec company-caddy getent hosts
host.docker.internal` (ra 172.17.0.1, sai) và
`docker network inspect proxy-net` (gateway thật là 172.19.0.1).

## Firewall liên quan

UFW chỉ cho phép subnet `172.19.0.0/16` truy cập cổng 9119 trên host —
không public. Xem
[[../02_decisions/0002_caddy_https_not_ip_whitelist]].

## Rủi ro còn treo

Nếu mạng `proxy-net` bị xoá và tạo lại, Docker có thể cấp subnet khác →
`caddy_proxy_network_gateway` trong `group_vars/all.yml` sẽ sai và cần sửa
tay. Không có cơ chế tự phát hiện.
