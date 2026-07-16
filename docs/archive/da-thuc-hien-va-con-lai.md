# Đã tự sửa plan + tự triển khai code — báo cáo kết quả

Tôi không có quyền SSH vào VPS thật của bạn, nên "triển khai" ở đây nghĩa là: tôi đã trực tiếp sửa và bổ sung toàn bộ code còn thiếu vào repo Ansible (thay vì chỉ viết báo cáo gợi ý), tự kiểm thử mọi thứ có thể kiểm thử được trong sandbox (không cần VPS thật), và đóng gói lại thành `hermes-erpnext-telegram-ansible-v2.zip`. Phần còn lại — chạy trên VPS thật, tạo bot Telegram thật, chạy pilot với người dùng thật — bắt buộc phải có quyền truy cập hạ tầng thật của bạn.

## 1. Đã sửa trong repo gốc

- **Pin version**: `frappe_docker_ref` và `hermes_image` trước đây để `main`/`latest` (vi phạm chính nguyên tắc mục 14.5 của bản kế hoạch) — đã đổi thành tag cụ thể (`v0.6.0`, `ghcr.io/nousresearch/hermes-agent:2026.06.1`). Bạn cần tự xác minh các tag này còn tồn tại và đã test trước khi dùng thật, vì tôi không thể kiểm tra registry thật từ sandbox.
- **Tách staging**: thêm `inventories/staging/` đầy đủ (hosts + group_vars + vault example), mirror production nhưng domain/site/backup retention nhỏ hơn.
- Thêm profile **system-maintainer** (tắt theo mặc định, không gắn bot Telegram, không có ERPNext API key — đúng mục 6.4).

## 2. Đã xây mới hoàn toàn (trước đây plan chỉ mô tả, chưa có code)

### ERPNext custom app `hermes_ops` (`apps/hermes_ops/`)
- Custom field cho Project/Task/Lead/Opportunity (27 field, đúng danh sách mục 8.1–8.3).
- DocType **Telegram Identity** + **Telegram Identity Link Code** (onboarding `/link`, mục 5.5).
- DocType **AI Approval Request** — có kiểm tra: không tự duyệt yêu cầu của chính mình, payload đổi sau khi hash thì approval vô hiệu, tự động expire (mục 8.4).
- DocType **Telegram Message Route** + **Telegram Message Event** — bảng chống lặp với `hop_count` tối đa 2, không xử lý lại `event_id` (mục 5.6–5.8).
- 3 Role: Hermes Ops Admin / Hermes Staff / Hermes Sales.
- Playbook `provision_erpnext.yml` tạo API user riêng cho từng profile (không cấp Administrator), ghi secret ra file cục bộ đã gitignore để bạn tự copy vào Vault.

### ERPNext API Bridge (`integration/erpnext-bridge/`)
Đây là phần quan trọng nhất còn thiếu trước đây — lớp duy nhất được phép gọi ERPNext thay Hermes:
- 15 read tool, 11 safe-write tool, 6 approval tool — đúng danh sách mục 9.1–9.3.
- JSON Schema validate input, idempotency key bắt buộc cho mọi write, audit log (không log secret), rate limit theo profile, không trả traceback thô.
- Danh sách forbidden tool (`erp_execute_sql`, `erp_call_any_endpoint`...) không tồn tại trong code — có test tự động khẳng định điều này.
- **9 test tự động, chạy thật trong sandbox, tất cả pass**: xác thực bearer token đúng profile, tool lạ trả 404, thiếu idempotency_key bị từ chối, progress ngoài 0–100 bị chặn trước khi chạm ERPNext, và quan trọng nhất — gọi trùng cùng idempotency_key thì ERPNext chỉ bị gọi đúng 1 lần (verify bằng respx mock, đếm số lần gọi thật).
- Dockerfile chạy non-root, container `read_only`, không mount Docker socket.

### 6 skill lõi (`skills/`)
Theo đúng khuôn mẫu SKILL.md của bản kế hoạch (trigger, input, allowed/forbidden tools, procedure, idempotency, test cases): `staff-my-tasks`, `staff-update-progress` (đầy đủ nhất, có 6 test case bao gồm ambiguous-task, duplicate-request, timeout), `staff-daily-report`, `admin-daily-summary`, `admin-create-task`, `crm-create-lead`. Còn khoảng 24 skill khác trong danh sách gốc chưa viết — nên viết tiếp dần khi pilot mở rộng, không nên làm hết cùng lúc.

### Monitoring + off-site backup
- `roles/monitoring`: health-check script-only cron (không dùng LLM) chạy 07:45, kiểm tra HTTPS endpoint, container, dung lượng đĩa, tuổi bản backup gần nhất — chỉ gửi Telegram khi có lỗi.
- Backup 3 tầng (14 ngày / 8 tuần / 6 tháng) thay vì xóa cứng theo 1 mốc, cộng thêm đồng bộ off-site qua rclone (`backup_offsite_enabled`, cấu hình remote qua Vault) — trước đây README tự liệt đây vào "giới hạn của starter", giờ đã có.

## 3. Đã tự kiểm thử trong sandbox (không cần VPS thật)

- `yamllint` toàn repo: sạch.
- `ansible-playbook --syntax-check` cho tất cả playbook: pass.
- Render thật toàn bộ template Jinja2 quan trọng (bridge.env, compose override, health-check.sh, backup script, profile.env, config.yaml, Caddyfile) bằng một playbook thử nghiệm với biến giả lập — **phát hiện và sửa 1 lỗi thật**: cú pháp `${#FAILURES[@]}` trong bash bị Jinja2 hiểu nhầm thành comment tag, đã sửa lại bằng cách đổi cách đếm lỗi.
- `bash -n` cho các script sinh ra: hợp lệ.
- `pytest` cho ERPNext API Bridge: 9/9 pass, bao gồm test idempotency là test quan trọng nhất.

## 4. Việc tôi KHÔNG thể làm thay bạn

- Chạy `ansible-playbook site.yml` thật trên VPS — cần bạn cấp SSH access.
- Tạo bot Telegram thật qua BotFather — cần tài khoản Telegram của bạn.
- Xác minh tag `frappe_docker_ref`/`hermes_image` tồn tại trên registry thật.
- Chạy pilot với người dùng thật (Phase 9).
- Cấu hình remote off-site backup thật (S3/R2/B2) — cần tài khoản dịch vụ lưu trữ.

## 5. File đính kèm

- `hermes-erpnext-telegram-ansible-v2.zip` — repo đầy đủ đã sửa.
- `audit-va-ke-hoach-trien-khai.md` — báo cáo audit gốc (vẫn còn giá trị tham chiếu phase/gate).
EOF
