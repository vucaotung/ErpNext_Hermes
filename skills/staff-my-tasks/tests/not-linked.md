**Input:** "việc của tôi hôm nay" (từ Telegram user ID chưa có Telegram Identity)

**Expect:**
- Skill KHÔNG gọi erp_list_my_tasks (bridge sẽ 401 vì không map được identity).
- Trả lời hướng dẫn nhân viên liên hệ admin để lấy mã /link.
