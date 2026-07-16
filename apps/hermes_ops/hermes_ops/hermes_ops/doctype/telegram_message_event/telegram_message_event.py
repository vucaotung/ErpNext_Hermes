"""Telegram Message Event — anti-loop ledger for cross-message routing
(mục 5.8). Every delivery attempt through a Telegram Message Route must
insert exactly one row keyed by event_id before it is allowed to send.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, now_datetime

MAX_HOP_COUNT = 2
RETENTION_DAYS = 30


class TelegramMessageEvent(Document):
    def before_insert(self):
        if not self.created_at:
            self.created_at = now_datetime()


def enforce_hop_limit(doc, method=None):
    if doc.hop_count > MAX_HOP_COUNT:
        frappe.throw(
            f"hop_count {doc.hop_count} exceeds the maximum of {MAX_HOP_COUNT} — "
            "refusing to relay further to prevent a message loop (mục 5.8)"
        )
    if frappe.db.exists("Telegram Message Event", doc.event_id):
        frappe.throw(f"event_id {doc.event_id} already processed — not reprocessing")


def prune_old_events():
    """Scheduled daily job — old anti-loop rows don't need to live forever."""
    cutoff = add_days(now_datetime(), -RETENTION_DAYS)
    frappe.db.sql(
        "DELETE FROM `tabTelegram Message Event` WHERE created_at < %s", (cutoff,)
    )
    frappe.db.commit()
