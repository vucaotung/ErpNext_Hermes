---
title: "Quyết định: mọi thao tác git ghi metadata phải chạy ngoài FUSE mount"
type: decision
status: current
created: 2026-07-24
updated: 2026-07-24
source: "PROJECT_HANDBOOK.md mục 9"
related: ["[[../03_incidents/2026-07-16_fuse_file_truncation_corrupted_first_commit]]"]
tags: [environment-bug, git, workflow]
---

# Quyết định: mọi thao tác git ghi metadata phải chạy ngoài FUSE mount

## Bối cảnh

`git init`, `git config`, `git remote add/set-url` chạy trực tiếp trên
folder Desktop (FUSE-mounted) từng làm hỏng `.git/config` nhiều lần — file
biến thành null byte hoặc "unknown error occurred while reading the
configuration files". Nguyên nhân: FUSE bridge không hỗ trợ đúng semantics
atomic-rename mà git dùng cho lockfile khi ghi config.

## Quyết định

Mọi thao tác **ghi metadata git** (không phải nội dung file thường) — init,
config, remote, commit, push — chạy trong 1 clone sạch ở filesystem thật
(`/tmp/repo_ssh` hoặc tương đương), KHÔNG BAO GIỜ chạy trực tiếp trên
đường dẫn FUSE-mounted. Sau khi xong, chỉ `cp -r` thư mục `.git` đã hoàn
chỉnh đè lên bản trên Desktop (thao tác copy file thường, không phải git
command sống).

## Quy trình chuẩn (đã dùng lặp lại nhiều lần trong dự án)

```bash
rm -rf /tmp/repo_ssh   # dọn nếu có sandbox restart giữa chừng
git clone git@github-erpnext-hermes:vucaotung/ErpNext_Hermes.git /tmp/repo_ssh
cd /tmp/repo_ssh
# ... sửa file, git add, git commit, git push ...
rm -rf "<desktop-path>/.git"   # cần allow_cowork_file_delete trước
cp -r /tmp/repo_ssh/.git "<desktop-path>/.git"
cd "<desktop-path>" && git config core.fileMode false   # FUSE không giữ exec bit đúng
git status --short   # phải rỗng
```

## Hệ quả cho agent tương lai

Nếu thấy `.git/config` lỗi/biến mất bất thường trên đường dẫn Desktop, đây
gần như chắc chắn là lại xảy ra lỗi này — đừng cố sửa trực tiếp, làm lại
theo quy trình trên.
