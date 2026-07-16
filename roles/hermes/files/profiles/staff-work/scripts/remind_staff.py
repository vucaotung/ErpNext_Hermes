#!/usr/bin/env python3
"""Cron job (--no-agent): sends each linked staff-work employee a Telegram
DM listing their tasks due today or overdue. Runs on a fixed schedule via
`hermes cron`, never invokes the LLM — deterministic, can't be skipped,
forgotten, or hallucinated (mục 6.4).
"""
import os
import sys
from datetime import date

import httpx

BRIDGE_BASE_URL = os.environ.get("BRIDGE_BASE_URL", "http://127.0.0.1:8642").rstrip("/")
BRIDGE_TOKEN = os.environ.get("BRIDGE_TOKEN", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

BRIDGE_HEADERS = {"Authorization": f"Bearer {BRIDGE_TOKEN}"}


def send_telegram(chat_id: str, text: str) -> None:
    httpx.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=10,
    )


def main() -> None:
    if not BRIDGE_TOKEN or not TELEGRAM_BOT_TOKEN:
        print("Missing BRIDGE_TOKEN or TELEGRAM_BOT_TOKEN", file=sys.stderr)
        return

    identities = httpx.get(
        f"{BRIDGE_BASE_URL}/identity/list", headers=BRIDGE_HEADERS, timeout=10
    ).json()["identities"]

    today = date.today().isoformat()
    sent = 0
    for identity in identities:
        telegram_user_id = identity["telegram_user_id"]
        resp = httpx.get(
            f"{BRIDGE_BASE_URL}/identity/tasks",
            params={"telegram_user_id": telegram_user_id},
            headers=BRIDGE_HEADERS,
            timeout=10,
        ).json()
        if not resp.get("linked"):
            continue

        tasks = resp.get("tasks", [])
        due_or_overdue = [
            t
            for t in tasks
            if t.get("exp_end_date") and t["exp_end_date"] <= today and t.get("status") != "Completed"
        ]
        if not due_or_overdue:
            continue

        lines = ["⏰ Nhắc việc hôm nay:"]
        for t in due_or_overdue:
            overdue = t["exp_end_date"] < today
            tag = "🔴 TRỄ HẠN" if overdue else "🟡 Đến hạn hôm nay"
            lines.append(f"- {t['name']}: {t['subject']} [{t['status']}] {tag}")
        send_telegram(telegram_user_id, "\n".join(lines))
        sent += 1

    print(f"Đã nhắc {sent} người.")


if __name__ == "__main__":
    main()
