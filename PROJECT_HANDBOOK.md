# Sổ tay dự án — ERPNext + Hermes Agent + Telegram

Tài liệu này đóng gói toàn bộ dự án tính đến ngày 2026-07-15: cấu trúc repo,
cách setup từ đầu, cheat sheet vận hành, hướng phát triển tiếp cho các phòng
ban khác, hướng dẫn để một AI agent khác (Claude Code, Codex...) đọc và tiếp
tục triển khai, và quy trình báo lỗi/yêu cầu tính năng.

Đối tượng đọc: Tùng (chủ dự án), admin/ops_admin vận hành hệ thống, và bất kỳ
AI coding agent nào được giao tiếp tục phát triển repo này.

---

## 1. Tổng quan & nguyên tắc cốt lõi

Hệ thống chạy trên 1 VPS nội bộ (production hiện tại: `173.249.51.69`, domain
`erp.enterpriseos.bond`), gồm:

- **ERPNext** (Frappe framework, qua `frappe_docker`) — nguồn sự thật duy nhất
  cho toàn bộ dữ liệu (Task, Project, Lead, Employee, Department...).
- **hermes_ops** — custom Frappe app thêm DocType riêng (Telegram Identity,
  AI Approval Request, Telegram Message Route/Event) và role/permission cho
  các profile Hermes.
- **Hermes Agent** — chạy nhiều "profile" độc lập, mỗi profile là 1 bot
  Telegram gắn với 1 nhóm người dùng (ops-admin, staff-work, sales-crm...).
- **ERPNext API Bridge** (`integration/erpnext-bridge`) — service FastAPI nội
  bộ, là **nơi DUY NHẤT** được phép gọi ERPNext REST API. Có whitelist tool
  cứng, JSON Schema validation, idempotency, rate limit, audit log.
- **Caddy** — reverse proxy + TLS.

Nguyên tắc không đổi qua các lần cập nhật (đã xác nhận từ `docs/PLANNING.md`):

1. ERPNext là source of truth — Telegram chỉ là messaging surface.
2. Hermes không bao giờ chạm MariaDB trực tiếp — mọi thao tác đi qua Bridge.
3. Mỗi Hermes profile có bot token + ERPNext API user + bridge shared secret
   **riêng** — không dùng chung, không cấp `Administrator` cho Hermes.
4. Whitelist tool cố định trong `integration/erpnext-bridge/app/tools/registry.py`
   — không có endpoint tùy ý (`erp_execute_sql`, `erp_call_any_endpoint`...
   bị cấm tuyệt đối, xem `FORBIDDEN_TOOL_NAMES` trong file đó).
5. Danh tính cá nhân qua Telegram **không bao giờ** để LLM tự khai báo — phải
   đi qua kênh không thể giả mạo (lệnh slash `/link`, xử lý ở tầng gateway
   hook, không qua LLM). Xem mục 7.
6. Secrets nằm trong Ansible Vault, không log, không commit.
7. Luôn pin version (`erpnext_version`, `frappe_docker_ref`, `hermes_image`),
   luôn test trên `inventories/staging` trước khi áp dụng `production`.

---

## 2. Kiến trúc & luồng dữ liệu

```
                         ┌─────────────────────────┐
   Telegram user ──────► │  Hermes profile (bot)    │
   (L1/L2/L3, đã /link)  │  ops-admin / staff-work  │
                         │  / sales-crm             │
                         └───────────┬─────────────┘
                                     │ HTTP + shared secret
                                     ▼
                         ┌─────────────────────────┐
                         │  ERPNext API Bridge      │  ← whitelist tool cứng
                         │  (FastAPI, port 8642)    │    idempotency/audit/rate-limit
                         └───────────┬─────────────┘
                                     │ REST API + API key/secret
                                     │ (1 user riêng / profile, least-privilege)
                                     ▼
                         ┌─────────────────────────┐
                         │  ERPNext (Frappe)        │  ← nguồn sự thật
                         │  + custom app hermes_ops │
                         └─────────────────────────┘
```

Danh tính cá nhân (mục 7 của sổ tay người dùng): mỗi Hermes profile dùng
**chung 1 bot Telegram** cho nhiều người, nhưng phân biệt từng người qua
DocType **Telegram Identity** (map `telegram_user_id` ↔ `erpnext_user`),
được gắn qua lệnh `/link <mã>` — xử lý ở tầng **gateway hook**
(`command:link`) chứ không qua LLM, nên không thể bị giả mạo bằng cách chat
"tôi là admin".

---

## 3. Cấu trúc thư mục (đã đối chiếu với repo thật)

```
hermes-erpnext-telegram-ansible/
├── README.md                     # Hướng dẫn cài đặt gốc (tiếng Việt, chi tiết)
├── site.yml                      # Playbook tổng: bootstrap → deploy → verify
├── ansible.cfg / requirements.yml
├── docs/
│   ├── OPERATIONS.md             # Runbook vận hành ngắn (logs, backup, update...)
│   └── PLANNING.md                # Nguyên tắc cốt lõi + trạng thái repo
│
├── inventories/
│   ├── production/group_vars/all.yml     # Biến production (⚠ xem mục 4 — đang là giá trị mẫu)
│   ├── production/group_vars/vault.yml.example
│   ├── production/hosts.yml
│   └── staging/...                        # Y hệt cấu trúc production, dùng để test trước
│
├── playbooks/
│   ├── bootstrap.yml            # Cài Docker, firewall, network, user vận hành
│   ├── deploy.yml                # erpnext-app → erpnext → erpnext-bridge → caddy → hermes → backup → monitoring
│   ├── create_site.yml           # Tạo site ERPNext lần đầu
│   ├── provision_erpnext.yml     # Tạo API user least-privilege cho mỗi Hermes profile
│   ├── update.yml / rollback.yml / backup.yml / verify.yml
│
├── roles/                        # Ansible roles tương ứng từng thành phần
│   ├── common/ docker/ networks/ firewall/
│   ├── erpnext/ erpnext-app/     # Compose ERPNext + cài custom app
│   ├── erpnext-bridge/           # Compose + .env cho service Bridge
│   ├── caddy/                    # Reverse proxy + TLS
│   ├── hermes/                   # Render config.yaml/profile.env/compose cho MỌI Hermes profile
│   ├── backup/                   # Backup 3 tầng (ngày/tuần/tháng) + rclone off-site
│   └── monitoring/               # Health-check script-only cron
│
├── apps/hermes_ops/               # Custom Frappe app — data model + logic
│   └── hermes_ops/hermes_ops/
│       ├── doctype/
│       │   ├── telegram_identity/            # Map telegram_user_id ↔ erpnext_user
│       │   ├── telegram_identity_link_code/  # Mã /link dùng 1 lần, hết hạn 15 phút
│       │   ├── ai_approval_request/          # Hàng đợi duyệt thao tác nhạy cảm
│       │   └── telegram_message_route/_event # Chống loop tin nhắn cross-platform
│       ├── fixtures/
│       │   ├── custom_field.json    # Custom field trên Project/Task/Lead/Opportunity
│       │   ├── custom_role.json     # Định nghĩa Role (Hermes Ops Admin/Staff/Sales/Director/Team Lead)
│       │   └── custom_docperm.json  # Quyền đọc/ghi từng Role trên từng DocType
│       ├── hooks.py                 # Đăng ký fixtures, doc_events, scheduler_events
│       └── provisioning.py          # Hàm provision user qua `bench execute` (không lộ qua HTTP)
│
├── integration/
│   ├── erpnext-bridge/            # Service Bridge — CHỈ nơi được gọi ERPNext API
│   │   ├── app/
│   │   │   ├── main.py             # FastAPI routes (tools/, identity/, healthz)
│   │   │   ├── auth.py              # Xác thực profile qua bridge shared secret
│   │   │   ├── config.py            # Đọc .env theo từng profile
│   │   │   ├── erpnext_client.py    # Wrapper gọi ERPNext REST API
│   │   │   ├── idempotency.py       # SQLite lưu idempotency_key đã xử lý
│   │   │   ├── rate_limit.py
│   │   │   ├── audit.py             # Ghi mọi lời gọi vào audit.log
│   │   │   └── tools/registry.py    # ⭐ WHITELIST TOOL — sửa file này để thêm/sửa năng lực Hermes
│   │   └── tests/                   # pytest — chạy độc lập, không cần VPS thật
│   └── erpnext-mcp-adapter/         # Adapter MCP gọi vào Bridge
│
└── skills/                         # Skill Hermes (mỗi skill = 1 hành vi hội thoại được duyệt)
    ├── staff-my-tasks/ staff-update-progress/ staff-daily-report/
    ├── admin-daily-summary/ admin-create-task/
    ├── crm-create-lead/
    └── <mỗi skill>/SKILL.md + schemas/input.json + schemas/output.json + tests/*.md
```

**Lưu ý quan trọng:** thư mục này **không phải git repo** (`git status` báo
`fatal: not a git repository`). Chưa có version control nào cho local
checkout này — xem khuyến nghị ở mục 9.1.

---

## 4. ⚠ Khoảng lệch giữa repo và VPS thật (sync gap)

Trong phiên làm việc gần nhất, phần lớn thay đổi cho **staff-work profile**
và **hệ thống phân quyền L1/L2 (Director/Team Lead)** được thực hiện **trực
tiếp trên VPS qua SSH/bench**, KHÔNG được đưa ngược lại vào repo local này.
Đối chiếu số dòng file thực tế:

| File | Trong repo local | Trên VPS thật (đã deploy) |
|---|---|---|
| `apps/hermes_ops/.../fixtures/custom_role.json` | 22 dòng (3 role) | 37 dòng (5 role — có Hermes Director, Hermes Team Lead) |
| `apps/hermes_ops/.../fixtures/custom_docperm.json` | 202 dòng | 302 dòng (thêm quyền Task/Project/Employee/Department cho Director & Team Lead) |
| `apps/hermes_ops/.../telegram_identity.json` | chưa có role Director/Team Lead | đã thêm |
| `apps/hermes_ops/hermes_ops/provisioning.py` | 46 dòng (chỉ `provision_profile`) | 144 dòng (thêm `provision_director`, `provision_team_lead`, `_ensure_human_user`, `_set_user_permission`) |
| `integration/erpnext-bridge/app/main.py` | 118 dòng | 352 dòng (thêm `/identity/link`, `/identity/tasks`, `/identity/list`, `/identity/assign_task`, `/identity/scope_report`) |
| `inventories/production/group_vars/all.yml` | vẫn là giá trị mẫu (`erp.example.com`, telegram ID giả) | VPS thật dùng `erp.enterpriseos.bond`, bot token thật `@ops_admin_val_bot`/`@staff_work_val_bot` |
| Hermes plugin/hook (`/link`, `/mytasks`, `/assign` command + cron script nhắc việc/báo cáo) | **không tồn tại trong repo** — các file này chỉ nằm trên VPS ở `/root/.hermes/profiles/<profile>/{plugins,hooks,scripts}/` | đã hoạt động live |

**Hệ quả:** nếu VPS bị mất hoặc cần dựng lại từ Ansible, toàn bộ phần L1/L2
và staff-work identity-linking sẽ **không được khôi phục** — vì Ansible chỉ
biết những gì có trong repo. Đây là việc ưu tiên cần làm sớm (xem mục 8.0).

---

## 5. Hướng dẫn setup từ đầu

Tóm tắt lại (đầy đủ, tự chứa) từ `README.md` gốc — làm theo đúng thứ tự:

### 5.1. Máy điều khiển (control machine)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install ansible
ansible-galaxy collection install -r requirements.yml
```

### 5.2. Inventory & Vault
Luôn cấu hình + test `inventories/staging/` trước, `inventories/production/`
sau. Mỗi environment có Vault riêng:
```bash
cp inventories/staging/group_vars/vault.yml.example inventories/staging/group_vars/vault.yml
ansible-vault encrypt inventories/staging/group_vars/vault.yml
```
Vault cần các biến: `vault_telegram_<profile>_bot_token`,
`vault_erpnext_<profile>_api_key/_api_secret`, `vault_offsite_access_key_id`
(rclone), `vault_openrouter_api_key`/`vault_tokenhub_api_key`.

### 5.3. Kiểm tra kết nối & dry-run
```bash
ansible all -i inventories/staging/hosts.yml -m ping --ask-vault-pass
ansible-playbook site.yml -i inventories/staging/hosts.yml --check --diff --ask-vault-pass
```

### 5.4. Triển khai hạ tầng
```bash
ansible-playbook site.yml -i inventories/staging/hosts.yml --ask-vault-pass
```
Chạy theo thứ tự: `bootstrap.yml` → `deploy.yml` (erpnext-app → erpnext →
erpnext-bridge → caddy → hermes → backup → monitoring) → `verify.yml`.

### 5.5. Tạo site ERPNext + cài custom app
```bash
ansible-playbook playbooks/create_site.yml -i inventories/staging/hosts.yml --ask-vault-pass
# Sau khi hoàn tất Setup Wizard trên web:
docker compose --project-name company-erpnext-staging -f /opt/apps/erpnext/generated/docker-compose.yml \
  exec backend bench get-app hermes_ops /workspace/custom-apps-src/hermes_ops
docker compose --project-name company-erpnext-staging -f /opt/apps/erpnext/generated/docker-compose.yml \
  exec backend bench --site <site> install-app hermes_ops
docker compose --project-name company-erpnext-staging -f /opt/apps/erpnext/generated/docker-compose.yml \
  exec backend bench --site <site> migrate
```

### 5.6. Cấp API user cho từng Hermes profile
```bash
ansible-playbook playbooks/provision_erpnext.yml -i inventories/staging/hosts.yml --ask-vault-pass
```
Kết quả ghi vào `generated-secrets-<host>.txt` (đã gitignore) — copy vào
`vault.yml` rồi **xóa file này ngay**. Không bao giờ cấp API key
`Administrator` cho Hermes.

### 5.7. Tạo bot Telegram
Tạo qua BotFather, mỗi profile 1 token riêng. Bật Privacy Mode; bot chỉ xử
lý mention/reply trong group; dùng numeric user ID + negative supergroup
chat ID (đã có sẵn trong `config.yaml.j2`).

### 5.8. Kiểm tra & test
```bash
ansible-playbook playbooks/verify.yml -i inventories/staging/hosts.yml --ask-vault-pass
ansible-playbook playbooks/backup.yml -i inventories/staging/hosts.yml --ask-vault-pass
cd integration/erpnext-bridge && pip install -r requirements-dev.txt && pytest tests/ -v
```

### 5.9. Checklist trước go-live
Xem nguyên văn trong `README.md` mục 10 — tóm tắt: version đã pin & test,
`hermes_ops` cài đúng, 3 API user chỉ có đúng 1 role (không Administrator),
Bridge trả lỗi đúng khi gọi sai (test tự động), off-site backup đã restore
thử thành công, health-check đã test cảnh báo, review Compose sinh ra, chạy
pilot nhóm nhỏ trước khi mở rộng.

---

## 6. Cheat sheet — lệnh dùng hằng ngày

### Trạng thái & log
```bash
docker compose -f /opt/apps/hermes/compose.yaml ps
docker compose -p company-erpnext -f /opt/apps/erpnext/generated/docker-compose.yml ps
docker logs hermes-ops-admin --tail 200
docker logs hermes-staff-work --tail 200
docker logs erpnext-bridge --tail 200
```

### Bridge — audit & idempotency
```bash
tail -f /opt/apps/integration/erpnext-bridge/data/audit.log
sqlite3 /opt/apps/integration/erpnext-bridge/data/idempotency.sqlite3 \
  "select profile, tool_name, datetime(created_at,'unixepoch') from idempotent_calls order by created_at desc limit 20;"
```

### ERPNext — bench thông dụng
```bash
# Vào MariaDB console
docker compose --project-name company-erpnext -f /opt/apps/erpnext/generated/docker-compose.yml exec backend bench --site <site> mariadb

# Chạy 1 hàm Python bất kỳ trong hermes_ops (admin-only, không qua HTTP)
docker compose --project-name company-erpnext -f /opt/apps/erpnext/generated/docker-compose.yml \
  exec backend bench --site <site> execute hermes_ops.provisioning.provision_director \
  --args '["director@company.local", "Ten Giam Doc", "Ten Company"]'

# Migrate sau khi đổi fixtures (Role/Custom DocPerm/Custom Field)
docker compose ... exec backend bench --site <site> migrate
docker compose ... exec backend bench --site <site> clear-cache
```
⚠ **Bẫy đã gặp:** sau khi sửa `custom_docperm.json` cho 1 role **đã có sẵn**
Custom DocPerm row trong DB (vd Telegram Identity cho Hermes Staff),
`bench migrate` **không** ghi đè row cũ. Phải sửa trực tiếp bằng SQL:
```sql
UPDATE `tabDocPerm` SET `read`=1 WHERE parent="Telegram Identity" AND role="Hermes Staff";
```
rồi `bench clear-cache`. Với role hoàn toàn mới (chưa từng có row), migrate
hoạt động bình thường.

### Hermes CLI
```bash
hermes --profile <profile> plugins list --plain --no-bundled
hermes cron list
hermes cron create "0 8 * * *" --script remind_staff.py --no-agent --deliver <chat_id> --name remind-staff-morning
```

### Backup / health-check thủ công
```bash
sudo /usr/local/sbin/company-platform-backup
sudo /usr/local/sbin/company-platform-health-check
```

### Cấp lại / thu hồi Telegram Identity
Mở DocType **Telegram Identity** trong ERPNext, sửa `active`/`revoked_at`,
hoặc gọi hàm `revoke` qua `bench execute` với quyền System Manager.

### Duyệt AI Approval Request
Mở DocType **AI Approval Request**, nút Approve/Reject. Hệ thống tự chặn
nếu người duyệt trùng người yêu cầu hoặc payload đã đổi sau khi hash lưu.

---

## 7. Vai trò & phân quyền hiện tại (tóm tắt)

Đã có sổ tay chi tiết dành cho người dùng cuối
(`So_tay_su_dung_he_thong.docx`, đã gửi trước đó). Tóm tắt kỹ thuật:

| Cấp | Role ERPNext | Phạm vi | Cách truy cập |
|---|---|---|---|
| L0 | System Manager (Tùng) | Toàn quyền | Web + SSH |
| L1 | Hermes Director | 1 Company (qua User Permission `allow=Company`) | Web dashboard + bot `@ops_admin_val_bot` sau `/link` |
| L2 | Hermes Team Lead | 1 Department (qua User Permission `allow=Department`) | Web dashboard + bot `@ops_admin_val_bot` sau `/link` |
| L3 | Hermes Staff | Task/Project của chính mình | Bot `@staff_work_val_bot` sau `/link` |
| (dịch vụ) | Hermes Ops Admin / Hermes Sales | Theo profile, không phải người thật | API key/secret riêng cho từng profile |

Cơ chế phân quyền tự động: **User Permission** (`allow=Company`/`Department`,
`apply_to_all_doctypes=1`) — ERPNext tự lọc mọi list view/report/API call
theo phạm vi đó, **không cần code lọc ở tầng ứng dụng**. Xem
`hermes_ops/provisioning.py::_set_user_permission`.

Danh tính Telegram: bảng **Telegram Identity** map `telegram_user_id` ↔
`erpnext_user`, gắn qua lệnh `/link <mã 1 lần, hết hạn 15 phút>` — xử lý ở
**gateway hook** `command:link` (không qua LLM, không thể giả mạo). Chi tiết
cơ chế này nằm trong Hermes plugin/hook trên VPS (xem mục 4 — chưa có trong
repo).

---

## 8. Hướng phát triển tiếp

### 8.0. Việc cần làm ngay (ưu tiên cao)
1. **Đồng bộ VPS → repo**: copy toàn bộ file đã sửa trực tiếp trên VPS (mục 4)
   ngược lại vào repo local, rồi `git init` + commit — nếu không, VPS là
   "nguồn sự thật" duy nhất và không thể redeploy từ Ansible.
2. Cập nhật `inventories/production/group_vars/all.yml` với giá trị thật
   (`erp.enterpriseos.bond`, `telegram_admin_user_ids` thật...) — hiện vẫn
   là giá trị mẫu từ template.
3. Thêm 2 role mới (`Hermes Director`, `Hermes Team Lead`) và cơ chế
   provisioning L1/L2 vào `roles/hermes/` + một playbook
   `provision_org.yml` mới (tương tự `provision_erpnext.yml` nhưng gọi
   `provision_director`/`provision_team_lead`), để việc thêm Director/Team
   Lead mới không cần SSH thủ công.
4. Đưa 3 file plugin/hook Hermes (`erpnext-identity` plugin, `link-command`/
   `mytasks-command`/`assign-command` hooks, `remind_staff.py`/
   `report_managers.py` cron script) vào repo, ví dụ
   `roles/hermes/files/plugins/erpnext-identity/` +
   `roles/hermes/files/hooks/...`, và role Ansible `hermes` copy chúng vào
   `{{ hermes_root }}/{{ item.name }}/plugins|hooks|scripts/` khi deploy.

### 8.1. Mở rộng cho phòng ban khác (mẫu chung)
Repo đã có khung sẵn cho **sales-crm** (`enabled: false` trong `all.yml`) —
đây là ví dụ cụ thể nhất để làm theo khi thêm bất kỳ phòng ban nào
(Finance, HR, Kho vận...). Các bước, đúng thứ tự:

1. **Role & quyền** (`apps/hermes_ops/hermes_ops/fixtures/`):
   thêm 1 entry vào `custom_role.json` (role mới, `desk_access` tùy loại
   người dùng thật hay service account), thêm các entry `custom_docperm.json`
   cho từng DocType role đó cần đọc/ghi. Nhớ thêm tên role vào danh sách
   filter trong `hooks.py` (`fixtures = [...]`) — nếu không, `bench migrate`
   sẽ không cài fixture cho role mới.
2. **Custom Field** (nếu phòng ban cần field riêng trên DocType có sẵn):
   thêm vào `custom_field.json`.
3. **Whitelist tool** (`integration/erpnext-bridge/app/tools/registry.py`):
   thêm `ToolSpec` mới cho các hành động phòng ban đó cần — phân loại đúng
   `read` / `safe_write` (cần `idempotency_key`) / `approval` (luôn tạo AI
   Approval Request, không bao giờ tự thực thi). Không bao giờ thêm tool kiểu
   "gọi API bất kỳ" — xem `FORBIDDEN_TOOL_NAMES`.
4. **Provisioning** (`apps/hermes_ops/hermes_ops/provisioning.py`): nếu
   phòng ban có người thật cần dashboard login → thêm hàm kiểu
   `provision_director`/`provision_team_lead` (dùng `_ensure_human_user` +
   `_set_user_permission`). Nếu chỉ cần 1 service account cho bot → dùng lại
   `provision_profile`.
5. **Hermes profile** (`inventories/<env>/group_vars/all.yml`): thêm 1 entry
   vào `hermes_profiles` (theo đúng khuôn `sales-crm` đã có), set
   `enabled: true` khi sẵn sàng.
6. **Skill** (`skills/`): viết 1 thư mục skill mới theo khuôn
   `skills/staff-my-tasks/` — `SKILL.md` (Purpose/Trigger/Required
   inputs/Allowed tools/Forbidden actions/Procedure/Idempotency/Output),
   `schemas/input.json`, `schemas/output.json`, `tests/*.md` (happy-path +
   ít nhất 1 edge case).
7. **Bot Telegram**: tạo bot mới qua BotFather, thêm token vào Vault.
8. **Test**: chạy `pytest tests/ -v` trong `integration/erpnext-bridge`,
   test thủ công trên staging trước khi bật `enabled: true` ở production.

### 8.2. Backlog đã biết (từ `docs/PLANNING.md`, chưa làm)
- ~24 skill còn thiếu so với kế hoạch gốc (mới có 6/~30).
- Webhook ERPNext (Lead/Opportunity/Task update) → Bridge → Telegram Message
  Route, hiện chỉ có DocType + anti-loop enforcement, chưa nối dây thật.
- Dashboard giám sát trực quan (hiện chỉ có health-check cron dạng script).
- Off-site backup: `vault_offsite_access_key_id`... vẫn là `CHANGE_ME`,
  chưa restore-test thật.
- `vault_openrouter_api_key`/`vault_tokenhub_api_key`: chưa rõ có cần không
  vì DeepSeek qua OpenRouter đang là provider chính đang hoạt động.
- Pilot thật với người dùng thật (Phase 9 kế hoạch gốc) — chưa bắt đầu.

---

## 9. Hướng dẫn cho một AI agent khác tiếp tục triển khai

Nếu bạn là một AI coding agent được giao đọc repo này lần đầu, thứ tự đọc
hiểu nên là:

1. Đọc `docs/PLANNING.md` để nắm nguyên tắc cốt lõi (mục 1 ở trên) — **không
   được vi phạm** dù được yêu cầu, đặc biệt nguyên tắc "whitelist tool cứng,
   không endpoint tùy ý" và "danh tính không được LLM tự khai báo".
2. Đọc mục 4 của tài liệu này (sync gap) **trước khi tin bất kỳ điều gì**
   trong `inventories/production/group_vars/all.yml` — giá trị ở đó là mẫu,
   không phải giá trị VPS thật đang chạy. Luôn xác minh bằng cách SSH/kiểm
   tra trực tiếp thay vì suy luận từ file.
3. Đọc `integration/erpnext-bridge/app/tools/registry.py` để biết chính xác
   Hermes được phép làm gì — đây là nguồn sự thật về năng lực hệ thống, hơn
   là đọc skill hay đọc code Hermes.
4. Khi được yêu cầu thêm tính năng mới, luôn đi theo khuôn ở mục 8.1 (role →
   permission → whitelist tool → provisioning → profile → skill → bot →
   test) theo đúng thứ tự — bỏ qua 1 bước thường gây lỗi
   `PermissionError` khó debug (đã xảy ra thật, xem mục 6, phần bẫy
   `bench migrate`).
5. Trước khi sửa 1 file JSON fixture đã tồn tại (đặc biệt Custom DocPerm cho
   1 role đã có sẵn quyền), nhớ: `bench migrate` không ghi đè row DB đã tồn
   tại — phải tự chạy `UPDATE` SQL thủ công rồi `bench clear-cache`. Đây là
   lỗi đã gặp thật và tốn thời gian debug nếu không biết trước.
6. Khi thêm plugin/hook cho Hermes, nhớ: thư mục đúng là
   `~/.hermes/profiles/<profile>/plugins|hooks/`, **không phải**
   `~/.hermes/plugins/` toàn cục — biến `HERMES_HOME` trong systemd unit của
   từng profile quyết định nơi Hermes tìm plugin/hook. Đặt sai chỗ sẽ khiến
   Hermes không bao giờ thấy plugin (đã xảy ra thật, mất thời gian debug).
7. Danh tính người dùng Telegram chỉ nên đọc qua hook
   `command:<tên_lệnh>` (nhận `{platform, user_id, command, args}` từ tầng
   gateway, trước khi vào LLM) — **không bao giờ** thêm 1 tool MCP nhận
   tham số kiểu `user_id`/`email` do LLM tự điền để dùng cho việc phân
   quyền, vì tham số đó có thể bị người dùng yêu cầu LLM tự khai báo sai.
8. Trước khi tạo file `.docx`/`.pdf` hay bất kỳ tài liệu nào, luôn render và
   xem lại (không giao tài liệu chưa xem qua) — quy trình cụ thể nằm trong
   skill `docx` của hệ thống agent đang chạy.
9. Repo hiện **chưa có git** — nếu commit thay đổi, chạy `git init`,
   `.gitignore` nên loại trừ: `*.env`, `vault.yml` (bản đã giải mã),
   `generated-secrets-*.txt`, mọi API key/secret, `.venv/`.

### 9.1. Ví dụ cụ thể: "thêm phòng ban Finance"
Nếu được giao đúng việc này, các file cần sửa/tạo, đúng thứ tự:
```
apps/hermes_ops/hermes_ops/fixtures/custom_role.json      # + role "Hermes Finance"
apps/hermes_ops/hermes_ops/fixtures/custom_docperm.json   # + quyền trên Journal Entry, Payment Entry, GL Entry (read-only gợi ý ban đầu)
apps/hermes_ops/hermes_ops/hooks.py                        # thêm "Hermes Finance" vào 2 filter fixtures
integration/erpnext-bridge/app/tools/registry.py           # + erp_get_gl_summary, erp_list_pending_payments (category "read" trước, "approval" cho mọi thứ ghi tiền)
inventories/production/group_vars/all.yml                  # + entry "finance-crm" trong hermes_profiles, enabled: false ban đầu
skills/finance-daily-summary/SKILL.md + schemas/ + tests/  # theo khuôn admin-daily-summary
```
Sau đó: tạo bot Telegram, `provision_erpnext.yml` (thêm mapping trong
`profile_role_map`), test trên staging, review với người phụ trách Finance
trước khi `enabled: true` ở production.

---

## 10. Quy trình báo lỗi / yêu cầu tính năng (dành cho admin & ops_admin)

Hệ thống hiện **chưa nối** vào công cụ ticket nào (Linear/Jira/GitHub Issues
chưa kết nối ở phiên làm việc này). Trong lúc chưa có công cụ đó, dùng quy
trình nhẹ sau:

### 10.1. Khi phát hiện lỗi (bug)
1. Xác định mức độ nghiêm trọng:
   - **Nghiêm trọng** (hệ thống down, mất dữ liệu, bot không phản hồi cho
     nhiều người, sai quyền cho phép thấy dữ liệu không được xem) → báo
     admin (Tùng, vucaotung@gmail.com) **ngay lập tức** qua Telegram/điện
     thoại, không chờ quy trình bên dưới.
   - **Thường** (1 lệnh bot trả lời sai định dạng, chậm, lỗi hiển thị) →
     làm theo bước 2.
2. Thu thập thông tin tối thiểu trước khi báo:
   - Thời điểm xảy ra (giờ, ngày).
   - Bot/profile nào (`@ops_admin_val_bot` hay `@staff_work_val_bot`).
   - Nội dung tin nhắn đã gửi + phản hồi nhận được (chụp màn hình hoặc copy
     nguyên văn).
   - `docker logs <container> --tail 200` quanh thời điểm đó, nếu ops_admin
     có quyền truy cập VPS.
3. Ghi vào file `ISSUES.md` ở gốc repo (tạo nếu chưa có), theo mẫu:
   ```markdown
   ## [BUG] <mô tả ngắn> — 2026-07-15
   - Người báo: <tên>
   - Mức độ: Thường / Nghiêm trọng
   - Bot/profile: staff-work
   - Tái hiện: <các bước>
   - Kỳ vọng: <hành vi đúng>
   - Thực tế: <hành vi sai>
   - Log liên quan: <đính kèm hoặc mô tả>
   - Trạng thái: Mới
   ```
4. Báo admin qua Telegram/email kèm link hoặc nội dung mục vừa ghi.

### 10.2. Khi cần yêu cầu tính năng mới
1. Mô tả theo mẫu (ghi vào cùng `ISSUES.md`, mục riêng):
   ```markdown
   ## [FEATURE] <tên tính năng> — 2026-07-15
   - Người yêu cầu: <tên, vai trò L1/L2>
   - Vấn đề cần giải quyết: <mô tả bài toán, không chỉ giải pháp>
   - Đề xuất: <cách làm nếu có ý tưởng>
   - Phòng ban/profile liên quan: <ops-admin/staff-work/sales-crm/mới>
   - Mức ưu tiên: Thấp / Trung bình / Cao
   - Trạng thái: Mới
   ```
2. Với yêu cầu liên quan đến **quyền truy cập dữ liệu mới** hoặc **hành
   động ghi/xóa dữ liệu mới** — luôn cần Tùng (L0) duyệt trước khi triển
   khai, vì mọi thay đổi năng lực của Hermes đều đi qua whitelist tool
   (mục 8.1, bước 3) và ảnh hưởng bảo mật toàn hệ thống.
3. Admin/ops_admin **không tự thêm tool mới vào `registry.py`** hay tự sửa
   Custom DocPerm trên production — mọi thay đổi phải qua staging trước
   (mục 5), đúng quy trình ở mục 8.1.

### 10.3. Khi giao việc này cho AI agent (Claude Code/Codex...) xử lý
Đưa cho agent: nội dung mục trong `ISSUES.md` + đường dẫn tới tài liệu này
(`PROJECT_HANDBOOK.md`). Không đưa `.env`, `vault.yml` đã giải mã, hay bất kỳ
API key/secret nào — làm theo đúng quy trình "review bundle hằng tháng" đã
mô tả trong `docs/OPERATIONS.md` (chỉ đưa `skills/`, `tests/`,
`tools/registry.py`, và audit log đã lọc).

---

## 11. Liên hệ & tài liệu liên quan

- Admin/chủ dự án: **Tùng** — vucaotung@gmail.com
- Sổ tay người dùng cuối (L1/L2/L3): `So_tay_su_dung_he_thong.docx` (đã gửi)
- Runbook vận hành: `docs/OPERATIONS.md`
- Nguyên tắc & trạng thái kế hoạch: `docs/PLANNING.md`
- Whitelist năng lực hệ thống: `integration/erpnext-bridge/app/tools/registry.py`
