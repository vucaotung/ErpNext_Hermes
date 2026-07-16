"""Append-only audit log (mục 9.5). One JSON line per tool call: who,
which tool, correlation id, outcome — never the ERPNext API secret, never
full request/response bodies that might contain customer PII beyond what's
needed to debug ("Không log API Secret").
"""

import json
import time

from .config import settings


def log_call(profile: str, tool_name: str, correlation_id: str, status: str, detail: str = ""):
    entry = {
        "ts": time.time(),
        "profile": profile,
        "tool": tool_name,
        "correlation_id": correlation_id,
        "status": status,
        "detail": detail[:500],
    }
    with open(settings.audit_log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
