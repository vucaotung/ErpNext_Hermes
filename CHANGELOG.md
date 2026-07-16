# Changelog

Định dạng theo [Keep a Changelog](https://keepachangelog.com/) (không dùng
SemVer tuyệt đối vì đây là hạ tầng nội bộ, không phải thư viện — mỗi mục là
1 mốc triển khai/thay đổi đáng kể trên production hoặc trong repo).

## [Unreleased]
### Chưa làm (xem PROJECT_HANDBOOK.md mục 8.2 và tab Issues)
- ~24 skill còn thiếu so với kế hoạch gốc.
- Webhook ERPNext → Bridge → Telegram Message Route chưa nối dây thật.
- Off-site backup chưa cấu hình remote thật, chưa restore-test.
- Dashboard giám sát trực quan.
- Roster `hermes_org_people` (L1/L2) và Telegram ID thật còn rỗng/mẫu.
- Pilot thật với người dùng thật.

## [2026-07-16] — Đồng bộ VPS ↔ repo, bare-metal Hermes, L1/L2 provisioning
### Added
- `PROJECT_HANDBOOK.md`: tài liệu tổng — cấu trúc dự án, setup, cheat sheet,
  hướng phát triển thêm phòng ban, hướng dẫn cho AI agent khác, quy trình
  báo lỗi/yêu cầu tính năng.
- `playbooks/provision_org.yml`: provision L1 (Hermes Director) / L2 (Hermes
  Team Lead) từ roster `hermes_org_people`, thay vì SSH tay từng người.
- `roles/hermes/templates/hermes-gateway.service.j2`: systemd unit riêng cho
  từng Hermes profile (thay thế hoàn toàn cách tiếp cận Docker Compose cũ
  chưa từng khớp với triển khai thật).
- `roles/hermes/files/profiles/{ops-admin,staff-work}/{plugins,hooks,scripts}/`:
  plugin `erpnext-identity`, gateway hook `link-command`/`mytasks-command`/
  `assign-command`, và 2 script cron `--no-agent` (nhắc việc L3, báo cáo
  L1/L2) — trước đó chỉ tồn tại trên VPS, giờ đã vào repo.
- Role `Hermes Director`, `Hermes Team Lead` + Custom DocPerm tương ứng
  trong `apps/hermes_ops` (Task/Project/Employee/Department), cùng
  `_ensure_human_user`/`_set_user_permission`/`provision_director`/
  `provision_team_lead` trong `provisioning.py`.
- Endpoint `/identity/link`, `/identity/tasks`, `/identity/list`,
  `/identity/assign_task`, `/identity/scope_report` trong ERPNext API
  Bridge — nền tảng cho việc liên kết danh tính Telegram ↔ ERPNext theo
  từng người thay vì theo profile.

### Changed
- `inventories/production/group_vars/all.yml`: cập nhật giá trị thật —
  `erpnext_domain`/`erpnext_site_name` → `erp.enterpriseos.bond`,
  `erpnext_version` → `v15.98.1` (bản pin cũ `v15.32.0` đã lệch so với thực
  tế). Thêm `plugins: [erpnext-identity]` cho ops-admin/staff-work.
- `roles/hermes/`: viết lại hoàn toàn để khớp với thực tế bare-metal
  (systemd) của VPS thay vì giả định Docker Compose — bao gồm
  `tasks/main.yml`, `handlers/main.yml`, `templates/config.yaml.j2` (thêm
  section `plugins.enabled`), `templates/profile.env.j2` (sửa
  `BRIDGE_BASE_URL` từ hostname Docker không resolve được sang
  `127.0.0.1:8642`).

### Removed
- `roles/hermes/templates/compose.yaml.j2` — chưa từng khớp với triển khai
  thật, gây hiểu lầm về kiến trúc hệ thống.
- `hermes_image` (biến Ansible mô tả 1 kiến trúc Docker không tồn tại).

### Fixed (trực tiếp trên VPS production, không chỉ trong repo)
- 2 Hermes gateway (`ops-admin`, `staff-work`) trước đó chạy như tiến trình
  nền dưới phiên SSH gốc, không có systemd — sẽ không tự khởi động lại nếu
  VPS reboot. Đã tạo và enable
  `hermes-gateway-{ops-admin,staff-work}.service`, cắt chuyển sạch (không
  trùng lặp long-polling Telegram).
- `BRIDGE_BASE_URL=http://erpnext-bridge:8642` trong `.env` thật của cả 2
  profile — hostname kiểu Docker không resolve được từ host bare-metal,
  khiến mọi lệnh `/link`/`/mytasks`/`/assign` sẽ fail. Sửa thành
  `http://127.0.0.1:8642` (cổng Bridge đã publish ra loopback).

### Infrastructure
- Repo chuyển từ "không có version control" sang `git init` + lịch sử
  commit đầy đủ.

## [trước 2026-07-16] — Khung ban đầu (từ README/docs/PLANNING gốc)
- Hạ tầng VPS qua Ansible (Docker, firewall, network).
- ERPNext + custom app `hermes_ops` (data model: Telegram Identity, AI
  Approval Request, Telegram Message Route/Event).
- ERPNext API Bridge với whitelist tool, idempotency, audit log, rate limit,
  có test tự động.
- Khung 4 Hermes profile: `ops-admin`, `staff-work` (bật), `sales-crm`,
  `system-maintainer` (tắt).
- 6/~30 skill lõi cho pilot.
- Backup 3 tầng + off-site (rclone), health-check script-only cron.
