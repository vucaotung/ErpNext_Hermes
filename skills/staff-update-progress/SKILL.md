# staff-update-progress

## Purpose
Cập nhật tiến độ (%) của một task mà người dùng có quyền thao tác (mẫu chuẩn ở mục 10 của bản kế hoạch).

## Trigger
Kích hoạt khi người dùng nói:
- "Cập nhật task lên X%."
- "Task Landing Page đã hoàn thành 80%."
- "Tôi làm được X% rồi."

Không kích hoạt khi:
- Người dùng chỉ hỏi trạng thái (dùng staff-my-tasks).
- Không xác định được task cụ thể (nhiều task trùng tên).
- progress ngoài khoảng 0–100.

## Required inputs
- Đủ thông tin để xác định một task duy nhất (tên task, hoặc task_id nếu đã biết từ context).
- progress: số nguyên 0–100.

## Allowed tools
- erp_search_tasks
- erp_get_task
- erp_update_task_progress
- erp_add_task_comment

## Forbidden actions
- Không đổi assignee.
- Không đổi deadline.
- Không xóa task.
- Không cập nhật task không thuộc về người dùng hiện tại.

## Procedure
1. Nếu chỉ có tên task, gọi erp_search_tasks để tìm. Nếu >1 kết quả khớp, hỏi lại người dùng để chọn — không tự đoán.
2. Gọi erp_get_task để xác nhận task này thuộc quyền của người dùng.
3. Validate progress trong khoảng 0–100 (bridge cũng validate lại — xem tests/out-of-range.md).
4. Sinh idempotency_key = hash(task_id + progress + phút hiện tại) để tránh double-submit khi Telegram gửi trùng.
5. Gọi erp_update_task_progress với idempotency_key.
6. Nếu progress == 100, cân nhắc gợi ý người dùng dùng staff-complete-task (skill khác) để đổi status sang Completed thay vì tự đổi status ở đây.
7. Đọc lại kết quả trả về, xác nhận với người dùng.

## Idempotency
Bắt buộc mọi lần gọi erp_update_task_progress phải có idempotency_key. Gửi lại cùng key trong khung thời gian ngắn (ví dụ Telegram gửi trùng do mất mạng) phải trả về kết quả cũ, không ghi đè hai lần.

## Output
- Task, progress cũ (nếu biết), progress mới, thời điểm cập nhật.
