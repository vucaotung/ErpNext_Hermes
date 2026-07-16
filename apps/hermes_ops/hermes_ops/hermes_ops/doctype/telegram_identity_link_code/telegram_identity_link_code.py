"""Telegram Identity Link Code — a short-lived, single-use onboarding
code created by `telegram_identity.create_link_code` and consumed by
`telegram_identity.redeem_link_code` (mục 5.5 of the deployment plan).

This doctype has no behavior of its own beyond being a plain Document —
all the logic (hashing, expiry checks, single-use enforcement) lives in
telegram_identity.py, which owns the full onboarding flow. A controller
file is still required here because every non-child-table DocType must
resolve to a Python module of the same name, or Frappe fails to load it
(as seen when this file was missing: "Module import failed for Telegram
Identity Link Code").
"""

from frappe.model.document import Document


class TelegramIdentityLinkCode(Document):
    pass
