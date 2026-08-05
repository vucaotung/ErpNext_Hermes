"""Handles the /ingest <url> [legal|project] slash command. Fetches the
URL and pushes it into the Onyx knowledge base via the onyx-bridge
service (127.0.0.1:8643, a separate bridge from the ERPNext one - it
cannot read ERPNext and the ERPNext bridge cannot reach the internet).
Fires with the REAL Telegram user_id from Hermes' gateway
(context["user_id"]) for audit logging only - never something the LLM
supplies or could spoof, and not required for bridge auth (that's the
per-profile bearer token below).
"""

import os
import httpx

BRIDGE_BASE_URL = os.environ.get("ONYX_BRIDGE_BASE_URL", "http://127.0.0.1:8643").rstrip("/")
BRIDGE_TOKEN = os.environ.get("ONYX_BRIDGE_TOKEN", "")

VALID_TARGETS = {"legal", "project"}
DEFAULT_TARGET = "legal"


async def handle(event_type: str, context: dict):
    raw = (context.get("args") or context.get("raw_args") or "").strip()
    user_id = context.get("user_id")

    if not raw:
        return {
            "decision": "handled",
            "message": "Dùng: /ingest <url> [legal|project] — mặc định là legal nếu không chỉ định.",
        }

    parts = raw.split()
    url = parts[0]
    target = DEFAULT_TARGET
    if len(parts) > 1:
        candidate = parts[1].lower()
        if candidate not in VALID_TARGETS:
            return {
                "decision": "handled",
                "message": f"❌ Loại không hợp lệ: '{candidate}'. Dùng 'legal' hoặc 'project'.",
            }
        target = candidate

    if not (url.startswith("http://") or url.startswith("https://")):
        return {"decision": "handled", "message": "❌ URL phải bắt đầu bằng http:// hoặc https://"}

    try:
        resp = httpx.post(
            f"{BRIDGE_BASE_URL}/ingest_url",
            json={"url": url, "target": target, "requested_by": str(user_id) if user_id else "unknown"},
            headers={"Authorization": f"Bearer {BRIDGE_TOKEN}"},
            timeout=30,
        )
    except Exception as exc:
        return {"decision": "handled", "message": f"❌ Lỗi kết nối bridge: {exc}"}

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return {"decision": "handled", "message": f"❌ Không nạp được tài liệu: {detail}"}

    data = resp.json()
    title = data.get("title", url)
    already = data.get("already_existed", False)
    target_label = "Văn bản pháp luật" if target == "legal" else "Hồ sơ dự án"
    status_label = "đã cập nhật (đã tồn tại)" if already else "đã thêm mới"
    return {
        "decision": "handled",
        "message": f"✅ {status_label}: \"{title}\"\n→ Document Set: {target_label}",
    }
