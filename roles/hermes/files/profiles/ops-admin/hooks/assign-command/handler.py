"""Handles the /assign <task_id> <email> slash command. Fires with the
REAL Telegram user_id from Hermes' gateway (context["user_id"]) — never
something the LLM supplies. Calls the ERPNext API Bridge's
/identity/assign_task endpoint, which resolves the caller's own linked
ERPNext identity and enforces the L1 (Company) / L2 (Department) scope
server-side before actually assigning anything.
"""

import os
import httpx

BRIDGE_BASE_URL = os.environ.get("BRIDGE_BASE_URL", "http://127.0.0.1:8642").rstrip("/")
BRIDGE_TOKEN = os.environ.get("BRIDGE_TOKEN", "")


async def handle(event_type: str, context: dict):
    raw = (context.get("args") or context.get("raw_args") or "").strip()
    user_id = context.get("user_id")

    if not user_id:
        return {"decision": "handled", "message": "❌ Không xác định được Telegram user_id."}

    parts = raw.split(maxsplit=1)
    if len(parts) != 2:
        return {
            "decision": "handled",
            "message": "Dùng: /assign <task_id> <email nhân viên>\nVí dụ: /assign TASK-2026-00003 vincent@company.local",
        }
    task_id, assignee_email = parts[0], parts[1]

    try:
        resp = httpx.post(
            f"{BRIDGE_BASE_URL}/identity/assign_task",
            json={"telegram_user_id": str(user_id), "task_id": task_id, "assignee_email": assignee_email},
            headers={"Authorization": f"Bearer {BRIDGE_TOKEN}"},
            timeout=10,
        )
    except Exception as exc:
        return {"decision": "handled", "message": f"❌ Lỗi kết nối bridge: {exc}"}

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return {"decision": "handled", "message": f"❌ Không giao được việc: {detail}"}

    data = resp.json()
    return {
        "decision": "handled",
        "message": f"✅ Đã giao task {data['task_id']} cho {data['assigned_to']}.",
    }
