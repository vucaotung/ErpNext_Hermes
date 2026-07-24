---
title: "hermes-serve.service chạy nhầm lệnh, dashboard không có web UI thật"
type: incident
status: current
created: 2026-07-24
updated: 2026-07-24
source: "CHANGELOG.md [2026-07-24 #2]; commit c703919"
related: ["[[../01_architecture/hermes_bare_metal]]"]
tags: [hermes, dashboard, systemd]
---

# hermes-serve.service chạy nhầm lệnh, dashboard không có web UI thật

## Hiện tượng

Sau khi mở được `https://hermes.enterpriseos.bond/login` (xem
[[2026-07-24_ip_whitelist_locked_out_admin_on_travel]]), đăng nhập vẫn lỗi:

```
{"error":"Headless backend (hermes serve): web UI disabled - use `hermes dashboard` for the browser UI."}
```

Trang `/login` vẫn hiện HTML bình thường (trông như hoạt động) nhưng mọi API
thật (`POST /auth/password-login`, `GET /api/auth/providers`) đều bị từ
chối.

## Nguyên nhân gốc

`hermes-serve.service` (tồn tại trên VPS **từ trước khi** bất kỳ ai trong
phiên này động vào — không phải lỗi do thay đổi hạ tầng) có `ExecStart` gọi
lệnh **sai**: `hermes serve` (backend JSON-RPC/WebSocket thuần, headless,
KHÔNG có web UI) thay vì `hermes dashboard` (lệnh đúng để có web UI). Hai
lệnh trông giống nhau, cùng nghe cổng 9119, cùng render được `/login` (asset
tĩnh) — chỉ khác nhau ở tầng API thật.

## Bẫy phụ: `--skip-build` cần `web_dist` đã build sẵn

Lần đầu đổi `ExecStart` sang `hermes dashboard --skip-build`, unit
crash-loop im lặng (`✗ --skip-build was passed but no web dist found`) vì
chưa từng build (`npm install --workspace web && npm run build -w web`).
Debug qua `journalctl -u hermes-serve.service`, không phải qua HTTP response
(service không kịp bind port khi crash).

## Cách khắc phục

1. `cd /usr/local/lib/hermes-agent && npm install --workspace web && npm run
   build -w web` (build 1 lần, ~2 phút, cần chạy nền vì lâu hơn 45s).
2. `ExecStart=... hermes dashboard --host 0.0.0.0 --port 9119 --skip-build
   --no-open`.
3. Thêm task Ansible kiểm tra `hermes_cli/web_dist/index.html` tồn tại
   trước khi enable unit — fail rõ ràng thay vì crash-loop âm thầm nếu
   deploy lại trên máy khác.

## Xác minh

`curl -X POST /auth/password-login` với mật khẩu sai → `401
{"detail":"Invalid credentials"}` (đúng hành vi, không còn lỗi headless).

## Hệ quả cho agent tương lai

Khi thấy `hermes serve` trong bất kỳ script/unit nào cho mục đích **có web
UI**, đó gần như chắc chắn là nhầm lẫn — kiểm tra lại phải là `hermes
dashboard`.
