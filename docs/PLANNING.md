# Planning triển khai

Tài liệu planning đầy đủ (v2.0) nằm trong "Kế hoạch triển khai hệ thống AI
quản trị nội bộ" và trong `docs/audit-va-ke-hoach-trien-khai.md` (nếu có ở
kho tài liệu công ty) — bản audit đối chiếu kế hoạch với repo này.

Nguyên tắc cốt lõi (không thay đổi qua các lần cập nhật repo):
- ERPNext là source of truth.
- Telegram chỉ là messaging surface.
- Hermes không truy cập MariaDB trực tiếp — mọi thao tác đi qua ERPNext API Bridge.
- Mỗi Hermes profile dùng bot token + ERPNext API user + bridge shared secret riêng.
- Telegram Privacy Mode giữ bật và Hermes chỉ xử lý mention/reply.
- Không cấp API tùy ý cho model — whitelist tool cố định trong `integration/erpnext-bridge/app/tools/registry.py`.
- Secrets nằm trong Ansible Vault, không log, không commit.
- Pin phiên bản trước khi production; luôn test trên `inventories/staging` trước.

## Trạng thái hiện tại của repo (tính đến lần cập nhật này)

| Thành phần | Trạng thái |
|---|---|
| Hạ tầng VPS (Ansible, Docker, firewall, network) | Hoàn thành |
| Staging + Production inventory tách biệt | Hoàn thành |
| ERPNext container + custom app `hermes_ops` (data model) | Hoàn thành (cần cài đặt + test thật trên staging) |
| Provisioning API user theo role tối thiểu | Hoàn thành (playbook `provision_erpnext.yml`) |
| ERPNext API Bridge (whitelist tool, idempotency, audit log, rate limit) | Hoàn thành, có test tự động (`integration/erpnext-bridge/tests`) |
| Hermes profiles (ops-admin, staff-work, sales-crm, system-maintainer) | Hoàn thành khung; sales-crm/system-maintainer để `enabled: false` |
| Skills | 6/~30 — đủ cho pilot nhỏ, còn lại cần viết thêm |
| Cross-message / anti-loop | Có DocType + enforcement ở ERPNext; chưa nối webhook Telegram thật |
| Backup 3 tầng + off-site | Hoàn thành (rclone), cần cấu hình remote thật + restore test |
| Monitoring / health-check | Hoàn thành (script-only cron), chưa có dashboard |
| Pilot | Chưa bắt đầu — cần môi trường thật + người dùng thật |

## Bước tiếp theo đề xuất

1. Deploy lên staging thật, chạy Phase 2 (tạo site, cài `hermes_ops`, tạo
   role/user mẫu) và Phase 6 gate (không có endpoint tùy ý, sai quyền trả
   lỗi rõ ràng — đã có test tự động, cần test lại trên staging thật với
   ERPNext thật thay vì mock).
2. Viết thêm skill còn thiếu theo đúng khuôn mẫu ở `skills/*/SKILL.md`.
3. Nối webhook ERPNext (Lead/Opportunity/Task update) vào bridge để kích
   hoạt Telegram Message Route thay vì chỉ có bảng dữ liệu.
4. Chạy pilot theo đúng Phase 9 của kế hoạch gốc trước khi mở rộng.
