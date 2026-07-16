# Planning triển khai

Tài liệu planning đầy đủ (v2.0) nằm trong
[`docs/archive/Ke-hoach-trien-khai-he-thong-AI-quan-tri-noi-bo.pdf`](archive/Ke-hoach-trien-khai-he-thong-AI-quan-tri-noi-bo.pdf)
(kế hoạch gốc) và
[`docs/archive/da-thuc-hien-va-con-lai.md`](archive/da-thuc-hien-va-con-lai.md)
(báo cáo đối chiếu: đã làm gì so với kế hoạch, tính đến lần cập nhật đó -
giữ lại làm tài liệu lịch sử, xem `PROJECT_HANDBOOK.md` mục 4/8 cho trạng
thái mới nhất).

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
| L1/L2 (Director/Team Lead) provisioning | Hoàn thành (`playbooks/provision_org.yml`), roster thật chưa điền |
| Hermes deploy (bare-metal + systemd) | Hoàn thành, đồng bộ với thực tế VPS 2026-07-16 |
| Pilot | Chưa bắt đầu — cần môi trường thật + người dùng thật |

## Bước tiếp theo đề xuất

Xem tab **Issues** của repo GitHub để có danh sách chi tiết, có nhãn ưu
tiên. Tóm tắt:

1. Viết thêm skill còn thiếu theo đúng khuôn mẫu ở `skills/*/SKILL.md`.
2. Nối webhook ERPNext (Lead/Opportunity/Task update) vào bridge để kích
   hoạt Telegram Message Route thay vì chỉ có bảng dữ liệu.
3. Điền roster L1/L2 thật + Telegram ID thật trước khi deploy production
   tiếp theo.
4. Chạy pilot theo đúng Phase 9 của kế hoạch gốc trước khi mở rộng.
