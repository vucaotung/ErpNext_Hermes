# admin-daily-summary

## Purpose
Tổng hợp báo cáo ngày cho admin (17:15, mục 11.1): số task hoàn thành/blocked/quá hạn, pipeline CRM tóm tắt.

## Trigger
- Hermes cron 17:15 hằng ngày.
- Admin chủ động hỏi: "báo cáo hôm nay thế nào".

## Required inputs
Không cần — phạm vi luôn là toàn công ty (đúng quyền ops-admin).

## Allowed tools
- erp_list_overdue_tasks
- erp_project_summary (cho từng project đang active)
- erp_pipeline_summary

## Forbidden actions
- Không tự động tạo Approval Request hay sửa dữ liệu trong lúc tổng hợp báo cáo.
- Không gộp dữ liệu tài chính/nhân sự chi tiết vào báo cáo Telegram (mục 5.9 — chỉ nêu "xem trong ERPNext").

## Procedure
1. Gọi erp_list_overdue_tasks — đây là danh sách bắt buộc phải có trong báo cáo.
2. Gọi erp_pipeline_summary để có tổng quan CRM.
3. Với mỗi project đang "Open"/"Working", gọi erp_project_summary nếu số project không quá lớn (nếu vượt ngưỡng hợp lý, chỉ nêu top N project rủi ro cao nhất thay vì liệt kê hết).
4. Soạn báo cáo: task quá hạn, task nguy cơ trễ, tóm tắt pipeline, không có số liệu bịa.
5. Gửi vào topic "Báo cáo" của supergroup (qua Telegram Message Route tương ứng).

## Idempotency
Chỉ đọc dữ liệu, không có write. Có thể chạy lại an toàn.

## Output
- Báo cáo: số task quá hạn, task rủi ro cao, tóm tắt pipeline theo giai đoạn.
