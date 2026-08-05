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

## Kiến trúc bộ nhớ ngoài ("Second Brain"): Onyx thay wiki/Obsidian (2026-08-05)

Quyết định: với dữ liệu **nghiệp vụ/pháp lý** (pháp chế, hồ sơ dự án), không
dùng mô hình wiki dạng Obsidian (`raw/` → `wiki/` → `output/` cục bộ trong
repo). Thay vào đó dùng **Onyx** (`https://onyx.enterpriseos.bond`) làm lớp
tri thức trung tâm — vì hệ thống này đã tồn tại, có RAG thật, và Tùng thao
tác trực tiếp qua chat thay vì phải tự biên tập note.

Ánh xạ 3 lớp:
- **raw** (dữ liệu gốc) → Google Drive connector của Onyx (tự động), lệnh
  `/ingest <url> [legal|project]` qua Hermes/Telegram, hoặc upload trực
  tiếp vào Onyx.
- **wiki** (tri thức có cấu trúc, tra cứu được) → chính Onyx (RAG search
  qua Document Set "Văn bản quy phạm pháp luật" / "Hồ sơ dự án"), không
  phải `docs/wiki/` của repo này.
- **output** (kết quả tạo ra — báo cáo, tài liệu tổng hợp) → **Google Drive
  của Tùng**, không ghi vào thư mục `output/` cục bộ trong repo.

Lưu ý quan trọng: `docs/wiki/` (Obsidian, trong repo này) **vẫn giữ
nguyên** — nhưng phạm vi của nó chỉ là bộ nhớ **kỹ thuật** cho AI agent làm
việc trên chính repo `ErpNext_Hermes` (kiến trúc, quyết định, sự cố khi
triển khai hạ tầng). Nó không còn được mô tả là "Second Brain" tổng quát
cho mọi loại tri thức — vai trò đó nay thuộc về Onyx cho dữ liệu nghiệp
vụ/pháp lý. Xem `docs/wiki/01_architecture/onyx_bridge.md` cho chi tiết
kỹ thuật của cầu nối Hermes↔Onyx, và CHANGELOG.md `[2026-08-01]`/`[2026-08-05]`.

Chưa làm (out of scope của thay đổi này): chưa có cơ chế tự động ghi
output do Hermes/Claude tạo ra thẳng vào Google Drive — hiện tại là quy
ước định hướng, cần chọn cơ chế cụ thể (Google Drive API riêng cho Hermes,
hay tái dùng connector của Onyx) trước khi triển khai.

## Bước tiếp theo đề xuất

Xem tab **Issues** của repo GitHub để có danh sách chi tiết, có nhãn ưu
tiên. Tóm tắt:

1. Viết thêm skill còn thiếu theo đúng khuôn mẫu ở `skills/*/SKILL.md`.
2. Nối webhook ERPNext (Lead/Opportunity/Task update) vào bridge để kích
   hoạt Telegram Message Route thay vì chỉ có bảng dữ liệu.
3. Điền roster L1/L2 thật + Telegram ID thật trước khi deploy production
   tiếp theo.
4. Chạy pilot theo đúng Phase 9 của kế hoạch gốc trước khi mở rộng.
