#!/usr/bin/env python3
"""Cron job (--no-agent): sends each linked L1 (Director) / L2 (Team Lead)
a Telegram DM with a task digest for their own Company/Department scope.
Runs on a fixed schedule via `hermes cron`, never invokes the LLM (mục 6.4).
"""
import os
import sys

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

    sent = 0
    for identity in identities:
        telegram_user_id = identity["telegram_user_id"]
        report = httpx.get(
            f"{BRIDGE_BASE_URL}/identity/scope_report",
            params={"telegram_user_id": telegram_user_id},
            headers=BRIDGE_HEADERS,
            timeout=10,
        ).json()
        if not report.get("linked") or not report.get("scope_type"):
            continue

        stats = report["stats"]
        scope_label = "công ty" if report["scope_type"] == "Company" else "phòng ban"
        lines = [
            f"📊 Báo cáo {scope_label} \"{report['scope_value']}\" ({report['employee_count']} nhân viên):",
            f"- Tổng task: {stats['total']}",
            f"- Đang mở: {stats['open']}",
            f"- Đang làm: {stats['working']}",
            f"- Hoàn thành: {stats['completed']}",
            f"- Trễ hạn: {stats['overdue']}",
        ]
        send_telegram(telegram_user_id, "\n".join(lines))
        sent += 1

    print(f"Đã gửi báo cáo cho {sent} người.")


if __name__ == "__main__":
    main()
