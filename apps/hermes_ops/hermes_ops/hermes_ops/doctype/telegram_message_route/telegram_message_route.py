"""Telegram Message Route — declarative routing config for which
ERPNext/Telegram events go to which chat/topic, under what delivery mode
(mục 5.9 of the deployment plan). Pure configuration doctype; all the
actual routing decisions are made by the code that reads these rows
(the bridge / Hermes skills), not by this controller.

A controller file is required for every non-child-table DocType even
when there is no custom behavior — see telegram_identity_link_code.py
for the same situation.
"""

from frappe.model.document import Document


class TelegramMessageRoute(Document):
    pass
