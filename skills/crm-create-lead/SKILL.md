# crm-create-lead

## Purpose
Tạo lead mới từ Telegram (sales-crm profile).

## Trigger
- "tạo lead công ty X, người liên hệ Y, số điện thoại Z"
- "thêm lead mới ..."

## Required inputs
- lead_name (bắt buộc)
- company_name, email, phone, source (tùy chọn, nhưng nên hỏi nếu thiếu source để báo cáo pipeline chính xác)

## Allowed tools
- erp_create_lead

## Forbidden actions
- Không tự động chuyển lead thành Opportunity (đó là quy trình nghiệp vụ riêng, không nằm trong skill này).
- Không tạo lead trùng lặp mà không cảnh báo — nếu nghi trùng, hỏi lại người dùng thay vì tự tạo bản sao (skill hiện tại không có tool tìm kiếm lead theo tên, ghi nhận đây là giới hạn cần bổ sung erp_search_leads ở phiên bản sau).

## Procedure
1. Xác nhận đủ lead_name.
2. Sinh idempotency_key, gọi erp_create_lead.
3. Xác nhận lại với người dùng: lead đã tạo, ID, các trường đã lưu.

## Idempotency
Bắt buộc idempotency_key cho erp_create_lead.

## Output
- Lead mới: ID, tên, công ty, trạng thái ban đầu.
