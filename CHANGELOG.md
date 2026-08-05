# Changelog

Định dạng theo [Keep a Changelog](https://keepachangelog.com/) (không dùng
SemVer tuyệt đối vì đây là hạ tầng nội bộ, không phải thư viện — mỗi mục là
1 mốc triển khai/thay đổi đáng kể trên production hoặc trong repo).
## [2026-08-01] — Kho tri thức pháp chế trên Onyx + lệnh /ingest cho Hermes

### Bối cảnh
Cần một kho tri thức RAG riêng cho "pháp chế" (văn bản quy phạm pháp luật +
hồ sơ dự án) mà Hermes có thể tự động nạp tài liệu vào khi được gửi link
qua Telegram, thay vì phải upload tay qua UI.

### Đã dựng
- **VPS Onyx mới** (169.58.107.168, Ubuntu 24.04) — cài Onyx chế độ
  Standard (full RAG: OpenSearch, Redis, model server, background worker),
  LLM DeepSeek trực tiếp, embedding local. RAM danh nghĩa 7.8GB thấp hơn
  mức khuyến nghị 10GB của Onyx nên thêm 8GB swap thay vì nâng cấp gói.
- 2 Document Set: "Văn bản quy phạm pháp luật" (cc_pair_id=2) và "Hồ sơ dự
  án" (cc_pair_id=3), mỗi cái có 1 File Connector seed + Onyx Access Token
  riêng (`hermes-ingestion`) để gọi Ingestion API.
- **`integration/onyx-bridge/`** — service FastAPI mới, độc lập hoàn toàn
  với `integration/erpnext-bridge/` (không đọc được ERPNext, và
  erpnext-bridge không ra được Internet). Chỉ làm đúng 1 việc: nhận URL,
  fetch + trích văn bản (có chặn SSRF vào IP nội bộ), đẩy vào Onyx
  Ingestion API theo đúng Document Set (`target: legal|project`). Cùng
  pattern xác thực/rate-limit/audit-log per-profile như erpnext-bridge,
  nhưng chạy bare-metal qua venv (không Docker) trên cổng 127.0.0.1:8643.
- **`roles/hermes/files/profiles/ops-admin/hooks/ingest-command/`** +
  **`.../plugins/onyx-ingest/`** — lệnh `/ingest <url> [legal|project]`
  mới cho Hermes, đúng pattern gateway hook đã dùng cho `/link`/`/assign`
  (nhận `user_id` Telegram thật từ gateway, không phải LLM tự suy ra —
  không thể giả mạo).
- Wiring vào `roles/hermes/templates/profile.env.j2` (biến
  `ONYX_BRIDGE_BASE_URL`/`ONYX_BRIDGE_TOKEN`, guard theo
  `item.onyx_ingest_enabled`) + `inventories/production/group_vars/all.yml`
  (bật `onyx_ingest_enabled: true` và thêm `onyx-ingest` vào danh sách
  `plugins` của profile `ops-admin`).

### Đã cân nhắc nhưng không chọn
- Free-form LLM tool/SKILL.md để agent tự quyết định "link này là pháp
  luật hay dự án rồi tự gọi API" — đã viết nháp
  (`admin-ingest-legal-doc/SKILL.md`) nhưng bỏ sau khi soi kiến trúc thật
  trên VPS production: mọi lệnh Telegram nhạy cảm (`/link`, `/assign`) đều
  dùng gateway hook xác định (deterministic), không phải LLM tool, vì hook
  nhận thẳng `user_id` từ gateway — an toàn hơn và nhất quán với phần còn
  lại của hệ thống.
- Onyx "Web Connector" có sẵn (tự crawl theo lịch) — không chọn vì user
  muốn kiểm soát chính xác link nào được nạp, khi nào, qua Telegram.

### Đã test
- Gọi trực tiếp Onyx Ingestion API với tài liệu thật
  (`https://costflow.vn/van-ban/xay-dung#gioi-thieu`) → 200, tạo doc mới.
- Gọi lại đúng URL đó qua `onyx-bridge` (`/ingest_url`, có bearer token
  per-profile thật) → 200, `already_existed: true`, trích đúng 21.307 ký
  tự, xác nhận toàn bộ chuỗi hook → bridge → Onyx hoạt động.
- `hermes-gateway-ops-admin.service` load hook `ingest-command` thành công
  sau khi bật plugin `onyx-ingest` và restart.

### Sự cố gặp phải khi triển khai
- `BRIDGE_REQUEST_TIMEOUT` mặc định 20s không đủ cho tài liệu thật (VPS
  dùng embedding local trên CPU, có swap) → tăng lên 60s.
- `hermes plugins enable onyx-ingest` có prompt xin quyền
  "allow_tool_override" (cho phép plugin ghi đè built-in tool) — đã lỡ
  chấp nhận (`true`) dù plugin chỉ đăng ký 1 slash command, không cần
  quyền này. Đã sửa lại `allow_tool_override: false` trong
  `config.yaml` của profile để đúng nguyên tắc least-privilege, khớp với
  `erpnext-identity` (plugin cũng chỉ đăng ký command, không có quyền
  này).
- Onyx `WEB_DOMAIN` bị để trống trong `.env` → OAuth callback (vd. Google
  Drive connector) redirect về `localhost:3000` thay vì IP thật, không
  load được. Sửa thành `http://169.58.107.168:3000`, recreate lại
  `api_server`/`web_server`/`nginx`.

### Chưa làm
- Domain + TLS cho Onyx (hiện chỉ truy cập qua `http://169.58.107.168:3000`).
- Test `/ingest` qua tin nhắn Telegram thật (mới test trực tiếp qua bridge
  bằng curl, chưa qua bot thật).
- Google Drive connector: `GOOGLE_OAUTH_CLIENT_ID`/`SECRET` vẫn trống,
  cần tạo OAuth app (Google Cloud Console) hoặc Service Account trước khi
  connector này dùng được — việc của user, chưa làm.
- Phase 2 (đã hoãn theo lựa chọn của user): agent tự tìm/tự crawl theo "ý
  tưởng nghiên cứu" thay vì chỉ theo link cụ thể.

## [2026-07-31] — Giải mã "+1 carried commit" của Hermes (issue #7) — không có patch ẩn
### Vấn đề
`hermes --version` trên VPS production báo `upstream f8b6d381 · local
48788032 (+1 carried commit)`, nghi ngờ có 1 patch local không có bản ghi
trong repo, cần điều tra trước khi cài lại Hermes ở nơi khác.

### Đã điều tra
- SSH vào VPS (`git log`/`git show 48788032 --stat`/`git diff f8b6d381
  48788032` tại `/usr/local/lib/hermes-agent`): repo cài đặt là **shallow/
  grafted clone** (`(grafted, HEAD -> main)`), chỉ có đúng 1 commit object
  cục bộ — không có lịch sử đầy đủ để so sánh với `f8b6d381`.
- Đối chiếu commit `48788032` với repo upstream NousResearch/hermes-agent
  qua GitHub API: **khớp 100%** SHA lẫn nội dung — `fix(tui): derive
  gateway-owned sources from the Platform enum, not a hardcoded list`, tác
  giả `teknium1`, 2026-07-08. Đây là commit chính thức đã có trên upstream,
  không phải patch tự chế cục bộ.

### Kết luận
"+1 carried commit" là hiển thị sai do giới hạn shallow-clone (git không
có object `f8b6d381` cục bộ nên so sánh lệch), không phải patch thật.
**An toàn để cài lại Hermes ở bất kỳ đâu (staging, disaster recovery...)
bằng đúng version tag hiện tại — không cần tìm/áp lại patch nào.** Đóng
issue #7.
## [Unreleased]
### Chưa làm (xem PROJECT_HANDBOOK.md mục 8.2 và tab Issues)
- ~24 skill còn thiếu so với kế hoạch gốc.
- Webhook ERPNext → Bridge → Telegram Message Route chưa nối dây thật.
- Off-site backup chưa cấu hình remote thật, chưa restore-test.
- Dashboard giám sát trực quan.
- Roster `hermes_org_people` (L1/L2) và Telegram ID thật còn rỗng/mẫu.
- Pilot thật với người dùng thật.

## [2026-07-24 #3] — Second Brain: wiki cho AI agent (docs/wiki/)
### Thêm
- `docs/wiki/` — vault Obsidian-style, 15 note atomic có YAML frontmatter,
  theo 5 nguyên tắc: ánh xạ theo kiến trúc thật, tách vòng đời (SSOT vs
  `99_archive/`), phẳng tối đa 3 cấp, tên file/frontmatter máy đọc được, và
  "phá vỡ là một quy trình" (không sửa đè lịch sử). Mục đích: agent AI (Claude,
  Hermes, Antigravity...) tra cứu nhanh sự thật/quyết định/sự cố đã biết mà
  không phải đọc lại toàn bộ PROJECT_HANDBOOK.md hay suy luận lại từ đầu.
- Nội dung ban đầu: 4 incident thật đã gặp trong dự án (FUSE truncation,
  hermes-serve vs hermes-dashboard, BRIDGE_BASE_URL DNS, IP-whitelist khoá
  admin), 3 quyết định kiến trúc (ADR ngắn), 3 note kiến trúc, 2 note vận
  hành, 1 glossary.
- `OBSIDIAN_VAULT_PATH` (biến mới `hermes_wiki_path: /root/wiki`) thêm vào
  `profile.env.j2` — Hermes dùng skill Obsidian có sẵn (bundled, miễn phí)
  để đọc/ghi vault này trực tiếp khi chat qua Telegram/dashboard.

### Đã cân nhắc nhưng không chọn
- Gemini Notebook API (trước đây NotebookLM API): cần Google Cloud project +
  add-on Gemini Enterprise/Education Premium trả phí riêng — không phù hợp
  cho mục đích wiki kỹ thuật miễn phí, self-hosted của dự án này.
- Skill `code-wiki` có sẵn trong Hermes (tự đọc source code sinh wiki): vẫn
  là lựa chọn tốt cho wiki *kỹ thuật thuần code* trong tương lai, nhưng
  không phải điều được yêu cầu ở đây (second brain rộng hơn, gồm cả quyết
  định/sự cố, không chỉ cấu trúc code).

### Chưa làm
- Chưa có cơ chế tự động đồng bộ `docs/wiki/` (repo) ↔ `/root/wiki` (VPS,
  Hermes đọc/ghi live) — xem `docs/wiki/04_operations/wiki_sync_process.md`.

## [2026-07-24 #2] — Sửa lệnh sai của chính hermes-serve.service (đã tồn tại từ trước)
### Vấn đề
- Sau khi mở được `https://hermes.enterpriseos.bond/login` (mục trên), đăng
  nhập vẫn lỗi: `{"error":"Headless backend (hermes serve): web UI disabled -
  use \`hermes dashboard\` for the browser UI."}`. Hoá ra unit
  `hermes-serve.service` từ trước tới giờ (kể cả trước khi tôi động vào gì)
  chạy nhầm lệnh `hermes serve` (backend JSON-RPC/WebSocket thuần, KHÔNG có
  web UI thật) thay vì `hermes dashboard` (lệnh đúng cho web UI). Trang
  `/login` vẫn render được (HTML tĩnh) nên trông như hoạt động, nhưng mọi
  API thật (`POST /auth/password-login`, `GET /api/auth/providers`...) đều
  từ chối phục vụ.

### Đã sửa (live + repo)
- Đổi `ExecStart` của `hermes-serve.service` sang
  `hermes dashboard --host 0.0.0.0 --port 9119 --skip-build --no-open`.
- `--skip-build` cần `hermes_cli/web_dist` đã được build sẵn - trước đó
  chưa từng build (`npm install --workspace web && npm run build -w web`),
  nên lần đầu đổi sang `hermes dashboard` unit crash-loop im lặng cho tới
  khi phát hiện qua journalctl. Đã build trực tiếp trên VPS.
- Thêm task Ansible mới kiểm tra `web_dist` tồn tại trước khi
  enable/start unit, fail rõ ràng kèm lệnh build đúng thay vì để
  crash-loop âm thầm ở lần deploy tiếp theo trên máy khác/VPS mới.
- Xác nhận cuối: `curl -X POST /auth/password-login` với mật khẩu sai trả
  về `401 {"detail":"Invalid credentials"}` (đúng hành vi), không còn lỗi
  "headless backend".
- Tùng xác nhận đăng nhập thành công vào `https://hermes.enterpriseos.bond/login`
  bằng mật khẩu đã nhớ lại từ lúc setup (username `admin`) - không cần reset.

### Đã đóng (trước đây "chưa làm")
- Ban đầu không rõ Tùng còn nhớ mật khẩu dashboard hay không (chỉ lưu dạng
  hash scrypt trong `/root/.hermes/config.yaml`, không đọc lại được) - đã
  xác nhận vẫn nhớ, không cần reset. Nếu sau này cần đặt lại: dùng
  `plugins.dashboard_auth.basic.hash_password()` để tạo hash mới.

## [2026-07-24] — Truy cập từ xa cho Hermes dashboard, hết phụ thuộc IP tĩnh
### Vấn đề
- Dashboard `hermes serve` (cổng 9119) chỉ cho phép truy cập qua UFW rule
  chặn theo IP admin cụ thể — mỗi lần đổi IP (đi công tác, đổi mạng) phải
  sửa firewall tay, và người dùng bị chặn hoàn toàn (timeout) cho tới lúc đó.
  Phát hiện trực tiếp khi Tùng báo "không truy cập được vào hermes desktop":
  log kernel cho thấy hàng loạt gói UFW BLOCK từ IP mới của Tùng nhắm đúng
  cổng 9119.

### Đã thêm (live VPS 2026-07-24, giờ đã đồng bộ vào repo)
- Subdomain `hermes.enterpriseos.bond` → Caddy → dashboard, có TLS thật
  (Let's Encrypt qua Caddy tự động, domain do Tùng thêm bản ghi A trên
  Namecheap). Không cần VPN, không cần cấu hình gì thêm trên máy khi di
  chuyển — chỉ cần trình duyệt + mật khẩu dashboard.
- Caddy container (mạng Docker riêng `proxy-net`) reverse-proxy tới dashboard
  đang chạy bare-metal trên host qua gateway IP của mạng đó
  (`172.19.0.1:9119`) — `host.docker.internal`/`host-gateway` KHÔNG dùng
  được ở đây vì nó trỏ vào bridge mặc định (docker0), không phải `proxy-net`.
  Xem comment trong `inventories/production/group_vars/all.yml`.
- UFW: xoá hết rule public/whitelist-theo-IP cho cổng 9119, thay bằng 1 rule
  duy nhất chỉ cho phép subnet nội bộ của `proxy-net` (172.19.0.0/16) —
  cổng 9119 giờ không thể truy cập trực tiếp từ Internet nữa, chỉ qua Caddy
  ở cổng 443.
- `fail2ban` (role mới `roles/fail2ban/`): đọc log JSON của Caddy cho site
  dashboard, ban IP sau 5 lần đăng nhập sai (401/403 vào
  `/auth/password-login`) trong 10 phút, ban 1 giờ.
- Systemd unit cho `hermes serve` chính nó (`roles/hermes/templates/hermes-serve.service.j2`)
  — trước đây chỉ tồn tại live trên VPS (tạo tay), chưa từng có trong repo.
- `caddy_email` trong `group_vars/all.yml` sửa từ placeholder
  `admin@example.com` thành giá trị thật đang dùng live.

### Chưa làm / rủi ro còn lại
- `caddy_proxy_network_gateway` (172.19.0.1) là hardcode theo subnet hiện
  tại của `proxy-net` — nếu network Docker này bị xoá/tạo lại với subnet
  khác, giá trị này phải cập nhật tay (không có auto-discovery trong role).
- Mật khẩu đăng nhập dashboard vẫn dùng cơ chế password-only có sẵn của
  Hermes (`BasicAuthProvider`) — chưa có 2FA.

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
