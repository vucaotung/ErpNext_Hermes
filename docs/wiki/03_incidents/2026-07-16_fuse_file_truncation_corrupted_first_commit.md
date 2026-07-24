---
title: "Sandbox FUSE mount âm thầm cắt cụt file khi ghi"
type: incident
status: current
created: 2026-07-24
updated: 2026-07-24
source: "PROJECT_HANDBOOK.md mục 9 điểm 10; commit 4281370"
related: ["[[0003_git_metadata_ops_must_happen_off_fuse_mount]]"]
tags: [environment-bug, git, ansible-repo]
---

# Sandbox FUSE mount âm thầm cắt cụt file khi ghi

## Hiện tượng

Môi trường agent (Claude/Cowork) làm việc trên folder Desktop của user qua 1
lớp FUSE mount. Có độ trễ/desync giữa view của tool ghi file (Write/Edit) và
view của shell (bash) đọc cùng file đó ngay sau. Kết quả: file bị ghi **cắt
cụt giữa chừng** mà không có lỗi nào báo ra — cả 2 phía (đĩa và git) đều
"khớp" ở trạng thái sai, nên `git diff` không phát hiện được tại thời điểm
ghi.

Hậu quả thật: `roles/erpnext-bridge/templates/compose.yaml.j2` bị cắt cụt
giữa 1 comment, thiếu hẳn phần `expose/ports/deploy/read_only/tmpfs/
security_opt/networks` — nằm im trong commit "Initial commit" của repo nhiều
ngày trước khi bị phát hiện tình cờ qua 1 lần `git status --short` thường lệ.

## Nguyên nhân gốc

Đặc tính của môi trường sandbox (FUSE bridge), không phải lỗi logic của
agent. Không tự sửa được ở tầng ứng dụng.

## Cách phát hiện

1. `wc -l` + `tail` file vừa ghi, so với số dòng kỳ vọng.
2. Với YAML/JSON/Python: parse thử (`yaml.safe_load`, `json.load`,
   `py_compile.compile`) — cú pháp sai lộ ra ngay.
3. Định kỳ: `git status --short` + `git diff --stat` toàn repo — nếu có file
   "tự nhiên" đổi mà không ai đụng vào, nghi ngay FUSE truncation.

## Cách khắc phục đã dùng

Sau bất kỳ Write/Edit nào **sẽ được commit**: verify bằng `wc -l`/`tail`
(và syntax check nếu là YAML/JSON/Python) trước khi tin file đó. Nếu lệch,
ghi lại trực tiếp qua bash heredoc (`cat > file << 'EOF'`) dùng nội dung đã
lấy từ Read tool, rồi verify lại.

## Hệ quả cho agent tương lai

Không giả định "Write tool báo thành công" = "file đúng". Luôn verify trước
khi git commit, đặc biệt với file dài (>50 dòng) hoặc chứa cấu trúc lồng
nhau (YAML nhiều cấp, JSON, code).
