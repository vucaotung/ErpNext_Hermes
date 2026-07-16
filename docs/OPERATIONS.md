# Runbook vận hành ngắn

## Trạng thái
```bash
docker compose -f /opt/apps/hermes/compose.yaml ps
docker compose -p company-erpnext -f /opt/apps/erpnext/generated/docker-compose.yml ps
docker compose -f /opt/apps/proxy/compose.yaml ps
docker compose -f /opt/apps/integration/erpnext-bridge/compose.yaml ps
```

## Logs
```bash
docker logs hermes-ops-admin --tail 200
docker logs hermes-staff-work --tail 200
docker logs erpnext-bridge --tail 200
docker compose -p company-erpnext -f /opt/apps/erpnext/generated/docker-compose.yml logs --tail 200 backend
```

## Bridge — audit log và idempotency
```bash
tail -f /opt/apps/integration/erpnext-bridge/data/audit.log
sqlite3 /opt/apps/integration/erpnext-bridge/data/idempotency.sqlite3 \
  "select profile, tool_name, datetime(created_at, 'unixepoch') from idempotent_calls order by created_at desc limit 20;"
```

## Backup tức thời
```bash
sudo /usr/local/sbin/company-platform-backup
```
Backup ghi vào `{{ backup_root }}/daily/<timestamp>`, tự động nhân bản sang
`weekly/` (Chủ Nhật) và `monthly/` (ngày 1), và đồng bộ off-site nếu
`backup_offsite_enabled: true`.

## Health check tức thời
```bash
sudo /usr/local/sbin/company-platform-health-check
```
Chạy tự động lúc 07:45 hằng ngày; chỉ gửi Telegram khi có lỗi.

## Cấp lại / thu hồi Telegram Identity
Trong ERPNext, mở DocType **Telegram Identity**, sửa `active`/`revoked_at`,
hoặc gọi `hermes_ops.hermes_ops.doctype.telegram_identity.telegram_identity.revoke`
qua `bench execute` với quyền System Manager.

## Duyệt / từ chối AI Approval Request
Trong ERPNext, mở DocType **AI Approval Request**, dùng nút Approve/Reject
(gọi `ai_approval_request.approve` / `.reject`). Hệ thống tự chặn nếu người
duyệt trùng người yêu cầu, hoặc nếu payload đã đổi sau khi hash được ghi lại.

## Cập nhật
1. Backup: `ansible-playbook playbooks/backup.yml --ask-vault-pass`.
2. Đổi phiên bản đã pin (`erpnext_version`, `frappe_docker_ref`, `hermes_image`,
   `bridge_image`) trong group_vars — luôn thử trên `inventories/staging` trước.
3. Chạy `ansible-playbook playbooks/update.yml -i inventories/staging/hosts.yml --ask-vault-pass`.
4. Chạy UAT trên staging (tạo/cập nhật task, tạo lead, gọi 6 skill lõi).
5. Lặp lại bước 2–3 cho `inventories/production`.

## Review bundle hằng tháng (mục 16 kế hoạch gốc)
```bash
mkdir -p review-bundle/{skills,tests,tool-inventory,recent-errors}
cp -r skills/* review-bundle/skills/
cp integration/erpnext-bridge/app/tools/registry.py review-bundle/tool-inventory/
tail -n 500 /opt/apps/integration/erpnext-bridge/data/audit.log > review-bundle/recent-errors/audit-tail.log
```
Không đưa `.env`, vault.yml, hay bất kỳ API key/secret nào vào `review-bundle/`.
Đưa bundle này cho Codex/Claude Code ở chế độ review-only trước, chỉ áp diff
theo từng batch sau khi đã xem báo cáo.
