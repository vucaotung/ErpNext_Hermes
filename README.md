# ErpNext_Hermes — ERPNext + Hermes Agent + Telegram

Hệ thống quản trị nội bộ: **ERPNext** làm nguồn dữ liệu duy nhất, **Hermes
Agent** làm trợ lý AI qua **Telegram** cho từng nhóm người dùng (ban giám
đốc, trưởng nhóm, nhân viên, sales), tất cả thao tác ghi/đọc đi qua một
**API Bridge** có whitelist tool cứng — không có endpoint tùy ý, không LLM
nào được tự khai báo danh tính người dùng.

Triển khai bằng Ansible lên 1 VPS, có staging/production tách biệt.

📖 **Đọc trước khi làm bất cứ việc gì:**
- [`PROJECT_HANDBOOK.md`](PROJECT_HANDBOOK.md) — cấu trúc dự án đầy đủ, cách
  setup, cheat sheet, hướng phát triển thêm phòng ban, hướng dẫn cho AI
  agent khác tiếp tục triển khai, quy trình báo lỗi/yêu cầu tính năng.
- [`docs/PLANNING.md`](docs/PLANNING.md) — nguyên tắc cốt lõi không đổi qua
  các lần cập nhật, và trạng thái từng hạng mục.
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md) — runbook vận hành ngắn (logs,
  backup, update, review bundle hằng tháng).
- [`docs/So_tay_su_dung_he_thong.docx`](docs/So_tay_su_dung_he_thong.docx) —
  sổ tay sử dụng dành cho người dùng cuối L1/L2/L3 (đăng ký, đăng nhập, dùng
  ERPNext web, dùng bot Telegram).
- [`docs/archive/`](docs/archive/) — kế hoạch triển khai gốc (PDF) và báo
  cáo đối chiếu lịch sử (giữ để tham khảo, không phải trạng thái mới nhất).
- [`CHANGELOG.md`](CHANGELOG.md) — lịch sử thay đổi theo mốc.

## Kiến trúc tóm tắt

```
Telegram user → Hermes profile (bot, bare-metal/systemd)
             → ERPNext API Bridge (FastAPI, whitelist tool cứng)
             → ERPNext (Frappe) + custom app hermes_ops
```

Thành phần chính:

- **ERPNext** qua `frappe_docker` production Compose, cộng thêm custom app
  **hermes_ops** (DocType Telegram Identity, AI Approval Request, Telegram
  Message Route/Event, custom field cho Project/Task/Lead/Opportunity, và
  role/permission cho toàn bộ phân cấp L0–L3, xem mục 7 của
  `PROJECT_HANDBOOK.md`).
- **ERPNext API Bridge** (`integration/erpnext-bridge`) — service FastAPI
  nội bộ, là nơi DUY NHẤT được phép gọi ERPNext REST API thay Hermes. Có
  JSON Schema validation, idempotency, rate limit, audit log.
- **Caddy** — reverse proxy và TLS.
- **Hermes Agent** — chạy bare-metal qua systemd (không phải Docker — xem
  `PROJECT_HANDBOOK.md` mục 4), nhiều profile độc lập (`ops-admin`,
  `staff-work`, `sales-crm`, `system-maintainer`), mỗi profile có Telegram
  bot token + ERPNext API user + bridge shared secret riêng.
- **Danh tính cá nhân qua Telegram** — mỗi profile dùng chung 1 bot cho
  nhiều người, phân biệt qua DocType Telegram Identity, gắn bằng lệnh
  `/link` xử lý ở tầng gateway hook (không qua LLM, không thể giả mạo).
- 6 skill lõi (`skills/`) cho pilot: staff-my-tasks, staff-update-progress,
  staff-daily-report, admin-daily-summary, admin-create-task, crm-create-lead.
- OpenRouter/DeepSeek là provider chính; Tencent TokenHub/HY là fallback.
- Backup cục bộ 3 tầng (ngày/tuần/tháng) + đồng bộ off-site qua rclone.
- Health-check script-only cron (không dùng LLM), cảnh báo qua Telegram.
- Ansible Vault cho secrets; inventory tách `production/` và `staging/`.

## Bắt đầu nhanh

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install ansible
ansible-galaxy collection install -r requirements.yml
```

Xem `PROJECT_HANDBOOK.md` mục 5 để có hướng dẫn setup đầy đủ, từng bước,
tự chứa (inventory/vault, dry-run, deploy, tạo site, provision API user +
L1/L2, tạo bot Telegram, checklist go-live).

## Trước khi bắt đầu — version pin

`inventories/production/group_vars/all.yml` pin `erpnext_version` và
`frappe_docker_ref`. **Luôn tự xác minh các tag này tồn tại và đã test trên
staging trước khi dùng cho production** — không dùng `main`/`latest`.

## Test

```bash
cd integration/erpnext-bridge
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Giới hạn hiện tại (xem `PROJECT_HANDBOOK.md` mục 8.2 để biết chi tiết + issue tracker)

- Chỉ có 6/~30 skill so với kế hoạch gốc.
- Webhook ERPNext (Lead/Opportunity/Task update) → Bridge → Telegram Message
  Route chưa nối dây thật (mới có DocType + anti-loop enforcement).
- Off-site backup chưa cấu hình remote thật, chưa restore-test.
- Dashboard giám sát trực quan chưa có (mới có health-check cron dạng script).
- Roster L1/L2 (`hermes_org_people`) và Telegram ID thật trong
  `group_vars/all.yml` vẫn là giá trị rỗng/mẫu, cần điền trước khi deploy
  production tiếp theo.
- Pilot thật với người dùng thật (Phase 9 kế hoạch gốc) chưa bắt đầu.

Xem toàn bộ backlog + issue đang mở tại tab **Issues** của repo này:
https://github.com/vucaotung/ErpNext_Hermes/issues

## Đóng góp / báo lỗi

Xem `PROJECT_HANDBOOK.md` mục 10 (quy trình báo lỗi/yêu cầu tính năng) và
mục 8.1 (khuôn mẫu để thêm 1 phòng ban/profile mới).
