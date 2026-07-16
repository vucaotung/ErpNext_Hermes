"""Handles the /mytasks slash command using the REAL Telegram user_id from
Hermes' gateway (context["user_id"]), resolved via the ERPNext API
Bridge's /identity/tasks endpoint — never trusts anything the LLM says
about "who is asking".
"""

import os
import httpx

BRIDGE_BASE_URL = os.environ.get("BRIDGE_BASE_URL", "http://127.0.0.1:8642").rstrip("/")
BRIDGE_TOKEN = os.environ.get("BRIDGE_TOKEN", "")


async def handle(event_type: str, context: dict):
    user_id = context.get("user_id")
    if not user_id:
        return {"decision": "handled", "message": "❌ Không xác định được Telegram user_id."}

    try:
        resp = httpx.get(
            f"{BRIDGE_BASE_URL}/identity/tasks",
            params={"telegram_user_id": str(user_id)},
            headers={"Authorization": f"Bearer {BRIDGE_TOKEN}"},
            timeout=10,
        )
    except Exception as exc:
        return {"decision": "handled", "message": f"❌ Lỗi kết nối bridge: {exc}"}

    if resp.status_code >= 400:
        return {"decision": "handled", "message": f"❌ Lỗi bridge: {resp.text}"}

    data = resp.json()
    if not data.get("linked"):
        return {
            "decision": "handled",
            "message": "Bạn chưa liên kết tài khoản ERPNext. Gõ /link <mã> trước (lấy mã từ admin).",
        }

    tasks = data.get("tasks", [])
    erpnext_user = data.get("erpnext_user", "?")
    if not tasks:
        return {"decision": "handled", "message": f"Không có task nào được gán cho {erpnext_user}."}

    lines = [f"📋 Task của {erpnext_user}:"]
    for t in tasks:
        due = t.get("exp_end_date") or "—"
        lines.append(f"- {t['name']}: {t['subject']} [{t['status']}] {t.get('progress', 0)}% (hạn: {due})")
    return {"decision": "handled", "message": "\n".join(lines)}
