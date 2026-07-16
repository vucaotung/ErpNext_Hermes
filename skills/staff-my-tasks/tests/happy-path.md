**Input:** "task nào của tôi đang trễ?" (từ nhân viên đã link Telegram Identity)

**Expect:**
- Skill gọi erp_get_current_user rồi erp_list_my_tasks.
- Không gọi bất kỳ tool nào khác.
- Trả lời bằng danh sách task, sắp theo priority/hạn, không có task của người khác.
