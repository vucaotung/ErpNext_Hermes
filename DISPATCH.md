# Yêu cầu tiếp nhận & triển khai tiếp — ErpNext_Hermes

Repo: https://github.com/vucaotung/ErpNext_Hermes

Bạn được giao tiếp tục phát triển hệ thống quản trị nội bộ ERPNext + Hermes
Agent (Telegram bot). Trước khi viết bất kỳ dòng code nào, đọc theo đúng
thứ tự sau:

1. **`README.md`** — tổng quan kiến trúc, thành phần chính.
2. **`PROJECT_HANDBOOK.md`** — bắt buộc đọc toàn bộ, đặc biệt:
   - Mục 1 (nguyên tắc cốt lõi) — **không được vi phạm** dù được yêu cầu.
   - Mục 4 (lịch sử đồng bộ VPS ↔ repo) — để biết cách xác minh trạng thái
     thật thay vì tin mù vào file cấu hình.
   - Mục 8.1 (khuôn mẫu thêm phòng ban/tính năng mới).
   - Mục 9 (hướng dẫn dành riêng cho AI agent tiếp theo — các bẫy đã gặp
     thật, đọc kỹ để không lặp lại).
3. **`docs/PLANNING.md`** — trạng thái từng hạng mục.
4. Tab **Issues** của repo — backlog đã được liệt kê cụ thể, có nhãn ưu
   tiên (`needs-decision` = phải hỏi Tùng trước khi làm).

## Nguyên tắc không được phá vỡ

- ERPNext là source of truth; Telegram chỉ là messaging surface.
- Hermes không bao giờ gọi ERPNext trực tiếp — mọi thao tác qua
  `integration/erpnext-bridge`, whitelist tool cứng trong `tools/registry.py`.
  Không thêm endpoint tùy ý.
- Danh tính người dùng Telegram không bao giờ để LLM tự khai báo — chỉ qua
  gateway hook (`command:link`, xem mục 7 của handbook).
- Secrets nằm trong Ansible Vault, không log, không commit.
- Luôn test trên `inventories/staging` trước `production`.

## Việc ưu tiên ngay (xem chi tiết + cách làm trong từng Issue)

1. Điền roster L1/L2 thật + Telegram ID thật (2 issue có nhãn
   `needs-decision` — cần xác nhận từ Tùng trước).
2. Viết thêm skill còn thiếu (issue #1).
3. Nối webhook ERPNext → Bridge → Telegram Message Route (issue #2).

Các việc còn lại xem đầy đủ trong tab Issues.

## Quy trình khi xong 1 việc

- Commit rõ ràng, mô tả đủ ngữ cảnh (xem `CHANGELOG.md`/lịch sử commit hiện
  có làm ví dụ về mức độ chi tiết mong muốn).
- Cập nhật `CHANGELOG.md` và phần liên quan trong `PROJECT_HANDBOOK.md` nếu
  thay đổi kiến trúc hoặc trạng thái 1 hạng mục.
- Đóng Issue tương ứng, ghi rõ đã làm gì/còn gì chưa xong.
- Không tự ý bật `enabled: true` cho profile mới hoặc cấp quyền dữ liệu mới
  trên production mà chưa qua staging + xác nhận từ Tùng.

## Liên hệ

Tùng — vucaotung@gmail.com (chủ dự án, người duyệt mọi thay đổi liên quan
quyền truy cập dữ liệu hoặc năng lực mới của Hermes).
