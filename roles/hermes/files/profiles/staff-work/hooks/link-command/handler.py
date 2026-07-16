"""Handles the /link <code> slash command. Fires with the REAL Telegram
user_id from Hermes' gateway (context["user_id"]) — never something the
LLM supplies or could spoof. Calls the ERPNext API Bridge's /identity/link
endpoint (not an LLM-callable tool) to redeem the one-time code generated
in ERPNext by an admin (create_link_code).
"""

import os
import httpx

BRIDGE_BASE_URL = os.environ.get("BRIDGE_BASE_URL", "http://127.0.0.1:8642").rstrip("/")
BRIDGE_TOKEN = os.environ.get("BRIDGE_TOKEN", "")


async def handle(event_type: str, context: dict):
    code = (context.get("args") or context.get("raw_args") or "").strip()
    user_id = context.get("user_id")

    if not code:
        return {"decision": "handled", "message": "Dùng: /link <mã> — lấy mã từ admin ERPNext trước."}
    if not user_id:
        return {"decision": "handled", "message": "❌ Không xác định được Telegram user_id."}

    try:
        resp = httpx.post(
            f"{BRIDGE_BASE_URL}/identity/link",
            json={"code": code, "telegram_user_id": str(user_id)},
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
        return {"decision": "handled", "message": f"❌ Không liên kết được: {detail}"}

    data = resp.json().get("result", {})
    erpnext_user = data.get("erpnext_user", "?")
    return {
        "decision": "handled",
        "message": f"✅ Đã liên kết Telegram của bạn với tài khoản ERPNext: {erpnext_user}",
    }
