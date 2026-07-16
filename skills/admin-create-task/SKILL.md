# admin-create-task

## Purpose
Cho phép admin tạo task và giao việc qua Telegram (mục 1, ví dụ mục 5.6 "Group sang DM": admin giao task kiểm tra API cho Nam, hạn 17:00).

## Trigger
- "giao task X cho Y, hạn Z"
- "tạo task ... trong project ..."

Không kích hoạt khi người dùng không phải ops-admin (staff-work/sales-crm không có tool này).

## Required inputs
- subject (nội dung task)
- project (nếu xác định được từ ngữ cảnh/topic)
- assignee mong muốn (tên nhân viên — cần map sang ERPNext user qua Telegram Identity)
- deadline (nếu có)

## Allowed tools
- erp_search_tasks (kiểm tra trùng lặp trước khi tạo)
- erp_create_task
- erp_add_task_comment

## Forbidden actions
- Không tự gán assignee trong erp_create_task nếu bridge/DocType chưa hỗ trợ field đó trực tiếp — việc gán người vẫn nằm trong nhóm "safe write" của Task (Task cho phép gán assignee khi tạo mới, khác với đổi assignee của task đã tồn tại, việc đó phải qua erp_request_task_reassignment).
- Không tạo task trùng (phải kiểm tra qua erp_search_tasks trước).

## Procedure
1. Xác định project từ ngữ cảnh (topic Telegram nếu có telegram_topic_id khớp) hoặc hỏi lại nếu không rõ.
2. Xác định nhân viên nhận việc qua Telegram Identity (không dùng tên tự do để suy đoán ERPNext user).
3. erp_search_tasks kiểm tra không có task trùng subject+project gần đây.
4. Sinh idempotency_key, gọi erp_create_task.
5. Xác nhận trong topic + gửi DM cho nhân viên nhận việc + tạo reminder (qua Hermes cron, không phải một tool riêng ở đây).

## Idempotency
Bắt buộc idempotency_key cho erp_create_task (mục 9.2).

## Output
- Task mới: ID, subject, project, deadline, người nhận.
