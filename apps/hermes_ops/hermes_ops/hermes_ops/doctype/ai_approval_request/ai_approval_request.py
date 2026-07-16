"""AI Approval Request — the only path for a Hermes skill to perform an
action the approval matrix (mục 12.4) marks as requiring a human.

Rules enforced here (mục 8.4):
  - Payload is hashed at creation. If the underlying record changes after
    approval such that the payload would no longer apply as-is, the hash
    check in the bridge's execute step must fail closed.
  - Approvals expire (`expires_at`); expired requests cannot be executed.
  - A request cannot be approved by the same ERPNext user who created it
    (Hermes must not approve its own request — mục 8.4 closing rule).
"""

import hashlib
import json

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class AIApprovalRequest(Document):
    def validate(self):
        if not self.payload_hash:
            self.payload_hash = _hash_payload(self.payload_json)

    def before_insert(self):
        if not self.requested_at:
            self.requested_at = now_datetime()


def _hash_payload(payload_json: str) -> str:
    normalized = json.dumps(json.loads(payload_json), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def validate_payload_hash(doc, method=None):
    if doc.payload_hash and doc.payload_hash != _hash_payload(doc.payload_json):
        frappe.throw(
            "Payload changed after the hash was recorded — this approval request "
            "is void. Create a new request instead of editing this one."
        )


def expire_stale_requests(doc, method=None):
    if doc.approval_status == "Pending" and doc.expires_at and doc.expires_at < now_datetime():
        doc.approval_status = "Expired"


def expire_all_stale_requests():
    """Scheduled hourly job (see hooks.py) — belt-and-suspenders in case a
    request is never opened again after expiry."""
    frappe.db.sql(
        """
        UPDATE `tabAI Approval Request`
        SET approval_status = 'Expired'
        WHERE approval_status = 'Pending' AND expires_at < %s
        """,
        (now_datetime(),),
    )
    frappe.db.commit()


@frappe.whitelist()
def approve(request_id: str):
    doc = frappe.get_doc("AI Approval Request", request_id)

    if doc.approval_status != "Pending":
        frappe.throw(f"Request is {doc.approval_status}, not Pending")
    if doc.expires_at < now_datetime():
        doc.approval_status = "Expired"
        doc.save(ignore_permissions=True)
        frappe.throw("Request has expired")
    if doc.requested_by == frappe.session.user:
        frappe.throw("A user cannot approve their own request (self-approval is not allowed)")
    if doc.payload_hash != _hash_payload(doc.payload_json):
        frappe.throw("Payload hash mismatch — request is void, create a new one")

    frappe.only_for(["System Manager", "Hermes Ops Admin"])

    doc.approval_status = "Approved"
    doc.approved_by = frappe.session.user
    doc.approved_at = now_datetime()
    doc.save(ignore_permissions=True)
    return {"status": "approved", "request_id": request_id}


@frappe.whitelist()
def reject(request_id: str, reason: str = None):
    doc = frappe.get_doc("AI Approval Request", request_id)
    frappe.only_for(["System Manager", "Hermes Ops Admin"])
    doc.approval_status = "Rejected"
    doc.approved_by = frappe.session.user
    doc.approved_at = now_datetime()
    if reason:
        doc.execution_result = f"Rejected: {reason}"
    doc.save(ignore_permissions=True)
    return {"status": "rejected", "request_id": request_id}
