# ERPNext + Hermes Agent + Telegram — Ansible + Data Model + API Bridge

Triển khai một VPS nội bộ gồm:

- ERPNext bằng `frappe_docker` production Compose + overrides, cộng thêm
  custom app **hermes_ops** (DocType Telegram Identity, AI Approval Request,
  Telegram Message Route/Event, custom field cho Project/Task/Lead/Opportunity).
- **ERPNext API Bridge** (`integration/erpnext-bridge`) — service FastAPI nội
  bộ, là nơi DUY NHẤT được phép gọi ERPNext REST API thay Hermes. Có JSON
  Schema validation, idempotency, rate limit, audit log, và whitelist tool
  cứng (không có endpoint tùy ý).
- Caddy làm reverse proxy và TLS.
- Nhiều Hermes profile (`ops-admin`, `staff-work`, `sales-crm`,
  `system-maintainer`), mỗi profile có Telegram bot token + ERPNext API user
  + bridge shared secret riêng.
- 6 skill lõi (`skills/`) cho pilot: staff-my-tasks, staff-update-progress,
  staff-daily-report, admin-daily-summary, admin-create-task, crm-create-lead.
- OpenRouter/DeepSeek là provider chính; Tencent TokenHub/HY là fallback.
- Backup cục bộ 3 tầng (ngày/tuần/tháng) + đồng bộ off-site qua rclone.
- Health-check script-only cron (không dùng LLM), cảnh báo qua Telegram.
- Ansible Vault cho secrets; inventory tách `production/` và `staging/`.

## 0. Trước khi bắt đầu — version pin

`inventories/production/group_vars/all.yml` đã pin `erpnext_version`,
`frappe_docker_ref`, `hermes_image` về các giá trị mẫu. **Bạn phải tự xác
minh các tag này tồn tại và đã test trên staging trước khi dùng cho
production** — không dùng `main`/`latest` (xem mục 14.5 của bản kế hoạch gốc).

## 1. Yêu cầu trên máy điều khiển

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install ansible
ansible-galaxy collection install -r requirements.yml
```

## 2. Cấu hình inventory

Luôn thử trên staging trước:

```text
inventories/staging/hosts.yml
inventories/staging/group_vars/all.yml
```

rồi mới áp dụng cho:

```text
inventories/production/hosts.yml
inventories/production/group_vars/all.yml
```

Tạo vault cho từng environment:

```bash
cp inventories/staging/group_vars/vault.yml.example inventories/staging/group_vars/vault.yml
ansible-vault encrypt inventories/staging/group_vars/vault.yml

cp inventories/production/group_vars/vault.yml.example inventories/production/group_vars/vault.yml
ansible-vault encrypt inventories/production/group_vars/vault.yml
```

## 3. Kiểm tra kết nối

```bash
ansible all -i inventories/staging/hosts.yml -m ping --ask-vault-pass
```

## 4. Dry run

```bash
ansible-playbook site.yml -i inventories/staging/hosts.yml --check --diff --ask-vault-pass
```

Lưu ý: Docker Compose và site creation có một số thao tác không mô phỏng hoàn toàn
trong check mode.

## 5. Triển khai hạ tầng và container (staging trước, production sau)

```bash
ansible-playbook site.yml -i inventories/staging/hosts.yml --ask-vault-pass
```

`site.yml` chạy: `bootstrap.yml` → `deploy.yml` (erpnext-app → erpnext →
erpnext-bridge → caddy → hermes → backup → monitoring) → `verify.yml`.

## 6. Tạo site ERPNext lần đầu

```bash
ansible-playbook playbooks/create_site.yml -i inventories/staging/hosts.yml --ask-vault-pass
```

Mở domain ERPNext, hoàn tất Setup Wizard, cài `hermes_ops`:

```bash
docker compose --project-name company-erpnext-staging \
  -f /opt/apps/erpnext/generated/docker-compose.yml \
  exec backend bench get-app hermes_ops /workspace/custom-apps-src/hermes_ops
docker compose --project-name company-erpnext-staging \
  -f /opt/apps/erpnext/generated/docker-compose.yml \
  exec backend bench --site erp-staging.example.com install-app hermes_ops
docker compose --project-name company-erpnext-staging \
  -f /opt/apps/erpnext/generated/docker-compose.yml \
  exec backend bench --site erp-staging.example.com migrate
```

## 7. Cấp API user cho từng Hermes profile

```bash
ansible-playbook playbooks/provision_erpnext.yml -i inventories/staging/hosts.yml --ask-vault-pass
```

Kết quả (API key/secret mỗi profile) được ghi vào file cục bộ
`generated-secrets-<host>.txt` (đã gitignore). Copy các giá trị này vào
`vault.yml` (`vault_erpnext_<profile>_api_key/_api_secret`) và **xóa file
này ngay sau đó**. Không cấp `Administrator` API key cho Hermes.

## 8. Tạo bot Telegram

Tạo bot bằng BotFather: một bot `ops-admin`, một bot `staff-work`, bot
`sales-crm` chỉ bật khi cần. Điền token vào Vault. Mỗi Hermes profile phải
dùng token riêng.

Khuyến nghị: Privacy Mode bật; bot chỉ xử lý mention hoặc reply trong group;
không để bot làm group admin nếu không cần; dùng numeric user ID và
negative supergroup chat ID (đã cấu hình sẵn trong `config.yaml.j2`).

## 9. Kiểm tra

```bash
ansible-playbook playbooks/verify.yml -i inventories/staging/hosts.yml --ask-vault-pass
ansible-playbook playbooks/backup.yml -i inventories/staging/hosts.yml --ask-vault-pass
```

Test bridge độc lập (không cần VPS thật):

```bash
cd integration/erpnext-bridge
pip install -r requirements-dev.txt
pytest tests/ -v
```

## 10. Production hardening — checklist trước go-live

- [ ] `frappe_docker_ref`, `erpnext_version`, `hermes_image` đã pin và test trên staging.
- [ ] `apps/hermes_ops` đã cài trên staging, custom field/DocType hiển thị đúng.
- [ ] `provision_erpnext.yml` đã chạy, 3 API user (`hermes-ops@`, `hermes-staff@`,
      `hermes-sales@`) chỉ có đúng role tương ứng, không có Administrator.
- [ ] ERPNext API Bridge trả lỗi đúng khi gọi tool không tồn tại, khi thiếu
      idempotency_key, khi progress ngoài 0–100 (xem `tests/`).
- [ ] Off-site backup (`backup_offsite_enabled: true`) đã cấu hình remote thật
      và đã restore-test thành công ít nhất một lần.
- [ ] Health-check cron đã nhận cảnh báo thử (tắt tạm một container để test).
- [ ] Review toàn bộ generated Compose.
- [ ] Chạy pilot với nhóm nhỏ (mục Phase 9 trong kế hoạch gốc) trước khi mở rộng.

## Giới hạn của bộ khung này

Khung này KHÔNG bao gồm:
- Toàn bộ ~30 skill trong kế hoạch gốc — chỉ có 6 skill lõi để pilot; skill
  còn lại (crm-*, admin-project-risk-review, quotation-create-draft...) cần
  viết thêm theo đúng khuôn mẫu trong `skills/`.
- Cross-message routing đầy đủ (mới có DocType + anti-loop enforcement ở
  tầng ERPNext, chưa có webhook/listener nối Telegram thật).
- Onboarding Telegram `/link` end-to-end (mới có `redeem_link_code`/
  `create_link_code` ở ERPNext; bot Telegram gọi các hàm này qua bridge cần
  được nối dây thêm).
- Dashboard giám sát trực quan (mới có script-only health-check cron).
- Pilot thật với người dùng.

Các phần trên nên triển khai theo đúng thứ tự Phase ở tài liệu kế hoạch gốc,
sau khi role matrix/approval matrix/data dictionary (Phase 0) được nghiệm thu.
