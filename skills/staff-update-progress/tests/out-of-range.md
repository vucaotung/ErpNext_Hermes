**Input:** "cập nhật lên 150%"

**Expect:** Skill validate trước khi gọi tool và từ chối; nếu vẫn gửi, bridge trả lỗi 422 "progress must be between 0 and 100" (xem integration/erpnext-bridge/tests/test_validation_and_idempotency.py::test_out_of_range_progress_is_rejected_by_handler) — không có ghi nào xảy ra ở ERPNext.
