from . import __version__ as app_version

app_name = "hermes_ops"
app_title = "Hermes Ops"
app_publisher = "Company"
app_description = "ERPNext data model for the Hermes Agent / Telegram integration"
app_email = "ops@company.local"
app_license = "Proprietary"
app_version = app_version

# Fixtures shipped with the app: custom fields on standard DocTypes and the
# Hermes-specific roles. Everything else (DocTypes) is installed as regular
# Frappe DocTypes under hermes_ops/hermes_ops/doctype/.
fixtures = [
    "Custom Field",
    {"dt": "Role", "filters": [["name", "in", [
        "Hermes Ops Admin",
        "Hermes Staff",
        "Hermes Sales",
        "Hermes Director",
        "Hermes Team Lead",
    ]]]},
    # Grants read/write/create on the standard doctypes each Hermes role is
    # allowed to touch (mục 6.1-6.3). Without these, a freshly created
    # custom role has zero permissions on any doctype and every bridge call
    # fails with frappe.exceptions.PermissionError even with a valid API
    # key (confirmed against a live site).
    {"dt": "Custom DocPerm", "filters": [["role", "in", [
        "Hermes Ops Admin",
        "Hermes Staff",
        "Hermes Sales",
        "Hermes Director",
        "Hermes Team Lead",
    ]]]},
]

# Keep AI Approval Request payloads immutable once approved: any change to
# the linked document after approval invalidates the approval (mục 8.4).
doc_events = {
    "AI Approval Request": {
        "validate": "hermes_ops.hermes_ops.doctype.ai_approval_request.ai_approval_request.validate_payload_hash",
        "before_save": "hermes_ops.hermes_ops.doctype.ai_approval_request.ai_approval_request.expire_stale_requests",
    },
    "Telegram Message Event": {
        "before_insert": "hermes_ops.hermes_ops.doctype.telegram_message_event.telegram_message_event.enforce_hop_limit",
    },
}

# Scheduled housekeeping: expire approvals past expires_at, prune old
# message events. Runs via Frappe's own scheduler, not Hermes cron —
# keeps loop-prevention state consistent even if Hermes is down.
scheduler_events = {
    "hourly": [
        "hermes_ops.hermes_ops.doctype.ai_approval_request.ai_approval_request.expire_all_stale_requests",
    ],
    "daily": [
        "hermes_ops.hermes_ops.doctype.telegram_message_event.telegram_message_event.prune_old_events",
    ],
}
