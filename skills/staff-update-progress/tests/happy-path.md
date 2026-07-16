**Input:** "Landing Page đã hoàn thành 80%." — task "Landing Page" khớp đúng 1 kết quả, thuộc về người dùng.

**Expect:** erp_search_tasks -> erp_get_task -> erp_update_task_progress(progress=80, idempotency_key=...) -> xác nhận với người dùng.
