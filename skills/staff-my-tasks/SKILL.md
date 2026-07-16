# staff-my-tasks

## Purpose
Liệt kê công việc của chính người dùng đang hỏi (staff-work profile).

## Trigger
- "task nào của tôi đang trễ?"
- "việc của tôi hôm nay"
- "tôi còn task gì chưa xong"

Không kích hoạt khi:
- Người dùng hỏi về task của người khác (ngoài phạm vi profile staff-work).
- Người dùng chưa được link Telegram Identity (mục 5.5) — trả lời hướng dẫn `/link`, không gọi tool.

## Required inputs
Không cần input bổ sung — profile tự xác định người dùng qua Telegram Identity đã link.

## Allowed tools
- erp_get_current_user
- erp_list_my_tasks

## Forbidden actions
- Không gọi erp_search_tasks với filter mở rộng sang task của người khác.
- Không hiển thị task thuộc project mà user không có quyền xem.

## Procedure
1. Gọi erp_get_current_user để xác nhận danh tính + role đang dùng.
2. Gọi erp_list_my_tasks (bridge tự lọc theo `_assign` chứa đúng ERPNext user của token — Hermes không tự truyền user khác).
3. Nếu danh sách rỗng, trả lời rõ "không có task nào" thay vì im lặng.
4. Sắp xếp theo priority rồi theo hạn (expected_end_date) khi trình bày.

## Idempotency
Read-only — không cần idempotency key.

## Output
- Danh sách task: tên, project, trạng thái, hạn, % tiến độ.
