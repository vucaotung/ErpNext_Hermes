# staff-daily-report

## Purpose
Sinh báo cáo cuối ngày của nhân viên (16:30 nhắc cập nhật, gửi trước 17:15 báo cáo admin — mục 11.1) và gửi vào DM + tóm tắt vào topic project liên quan (cross-message, mục 5.6).

## Trigger
- Hermes cron hằng ngày (không phải người dùng gõ lệnh trực tiếp).
- Người dùng chủ động: "gửi báo cáo hôm nay giúp tôi".

## Required inputs
Không cần input thủ công cho cron; nếu người dùng gọi thủ công thì không cần tham số.

## Allowed tools
- erp_list_my_tasks
- erp_get_project (để lấy telegram_group_id/telegram_topic_id nếu cần tóm tắt vào topic)

## Forbidden actions
- Không tự ý sửa task khi đang tổng hợp báo cáo (chỉ đọc).
- Không gửi báo cáo của người khác.

## Procedure
1. Gọi erp_list_my_tasks, lọc các task có cập nhật trong ngày hôm nay (progress/status thay đổi) hoặc còn mở.
2. Tổng hợp: số task hoàn thành, số đang làm, số bị block, task chưa có cập nhật.
3. Soạn báo cáo ngắn gọn bằng tiếng Việt, không suy diễn số liệu không có trong dữ liệu.
4. Gửi DM cho chính nhân viên.
5. Nếu có Telegram Message Route loại `Summarize` cho project liên quan và enabled, gửi bản tóm tắt vào topic project qua route đó (không tự bịa route mới).

## Idempotency
Không tạo bản ghi ERPNext mới — chỉ đọc + gửi tin nhắn. Cron chạy 1 lần/ngày; nếu chạy lại thủ công trong cùng ngày, báo cáo được phép gửi lại (không phải write operation cần chống trùng ở ERPNext), nhưng nên tránh spam bằng cách kiểm tra đã gửi lúc nào trong ngày.

## Output
- Bản tóm tắt: số liệu + danh sách task đáng chú ý (blocked, sắp hạn).
