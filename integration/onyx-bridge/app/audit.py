"""Append-only audit log. One JSON line per ingest call: who, url,
outcome - never the Onyx API key, never the full extracted document text.
"""

import json
import os
import time

from .config import settings


def log_call(profile: str, url: str, target: str, status: str, detail: str = ""):
    os.makedirs(os.path.dirname(settings.audit_log_path), exist_ok=True)
    entry = {
        "ts": time.time(),
        "profile": profile,
        "url": url,
        "target": target,
        "status": status,
        "detail": detail[:500],
    }
    with open(settings.audit_log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
