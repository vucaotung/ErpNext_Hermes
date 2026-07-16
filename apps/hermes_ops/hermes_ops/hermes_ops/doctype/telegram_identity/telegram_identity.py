"""Telegram Identity — maps a Telegram numeric user ID to an ERPNext user.

Onboarding flow (mục 5.5 of the deployment plan):

    Admin creates User + Employee
      -> generates a one-time link code (see `create_link_code`)
      -> employee opens the bot and sends /link <code>
      -> the ERPNext API Bridge calls `redeem_link_code`
      -> a Telegram Identity row is created/activated
      -> the code is invalidated (single use, short TTL)

This module intentionally does not talk to Telegram directly — the bridge
owns that. It only owns the identity/permission bookkeeping in ERPNext.
"""

import hashlib
import secrets
from datetime import timedelta

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

LINK_CODE_TTL_MINUTES = 15


class TelegramIdentity(Document):
    def before_insert(self):
        if not self.linked_at:
            self.linked_at = now_datetime()


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


@frappe.whitelist()
def create_link_code(erpnext_user: str, allowed_profile: str) -> dict:
    """Called by an admin (System Manager / Hermes Ops Admin) to generate a
    one-time onboarding code for a not-yet-linked employee. The plaintext
    code is returned once and never persisted — only its hash is stored on
    a pending Telegram Identity Link Code doc (see fixtures) with a TTL.
    """
    frappe.only_for(["System Manager", "Hermes Ops Admin"])

    code = secrets.token_hex(4).upper()  # e.g. "ABCD1234"
    expires_at = now_datetime() + timedelta(minutes=LINK_CODE_TTL_MINUTES)

    frappe.get_doc(
        {
            "doctype": "Telegram Identity Link Code",
            "erpnext_user": erpnext_user,
            "allowed_profile": allowed_profile,
            "code_hash": _hash_code(code),
            "expires_at": expires_at,
            "used": 0,
        }
    ).insert(ignore_permissions=True)

    return {"code": code, "expires_at": str(expires_at)}


@frappe.whitelist()
def redeem_link_code(code: str, telegram_user_id: str, telegram_username: str = None) -> dict:
    """Called only by the ERPNext API Bridge (never directly by Hermes or
    Telegram) after the bridge has verified the request came from the
    onboarding bot. Single-use: the matching link-code row is marked used
    and cannot be redeemed again.
    """
    code_hash = _hash_code(code)
    pending = frappe.get_all(
        "Telegram Identity Link Code",
        filters={"code_hash": code_hash, "used": 0},
        fields=["name", "erpnext_user", "allowed_profile", "expires_at"],
        limit=1,
    )
    if not pending:
        frappe.throw("Invalid or already-used link code")

    row = pending[0]
    if row.expires_at < now_datetime():
        frappe.throw("Link code expired — ask an admin to generate a new one")

    frappe.db.set_value("Telegram Identity Link Code", row.name, "used", 1)

    existing = frappe.db.exists("Telegram Identity", telegram_user_id)
    if existing:
        frappe.db.set_value(
            "Telegram Identity",
            existing,
            {
                "erpnext_user": row.erpnext_user,
                "allowed_profile": row.allowed_profile,
                "active": 1,
                "revoked_at": None,
                "telegram_username": telegram_username,
            },
        )
    else:
        employee = frappe.db.get_value("Employee", {"user_id": row.erpnext_user}, "name")
        frappe.get_doc(
            {
                "doctype": "Telegram Identity",
                "telegram_user_id": telegram_user_id,
                "telegram_username": telegram_username,
                "erpnext_user": row.erpnext_user,
                "employee": employee,
                "allowed_profile": row.allowed_profile,
                "active": 1,
            }
        ).insert(ignore_permissions=True)

    return {"status": "linked", "erpnext_user": row.erpnext_user, "allowed_profile": row.allowed_profile}


@frappe.whitelist()
def revoke(telegram_user_id: str):
    frappe.only_for(["System Manager", "Hermes Ops Admin"])
    frappe.db.set_value(
        "Telegram Identity", telegram_user_id, {"active": 0, "revoked_at": now_datetime()}
    )
