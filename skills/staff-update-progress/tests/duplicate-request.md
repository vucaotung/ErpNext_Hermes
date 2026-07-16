**Input:** Telegram gửi trùng tin nhắn "80%" hai lần do mất kết nối và client tự retry.

**Expect:** Cả hai lần dùng cùng idempotency_key (vì cùng task+progress+cùng phút) -> bridge trả `replayed: true` ở lần thứ hai, ERPNext chỉ ghi nhận một lần cập nhật (xem test_same_idempotency_key_is_not_executed_twice).
