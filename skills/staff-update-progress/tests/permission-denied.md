**Input:** người dùng cố cập nhật một task không thuộc `_assign` của mình.

**Expect:** erp_get_task trả về task nhưng skill nhận ra task không thuộc user hiện tại (không có trong danh sách erp_list_my_tasks) -> từ chối, không gọi erp_update_task_progress, giải thích lý do.
