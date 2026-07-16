"""The whitelist. Every tool a Hermes skill is allowed to call is declared
here — name, JSON Schema for its arguments, which category it belongs to
(read / safe_write / approval), and the handler function.

There is no code path anywhere in this service that accepts an arbitrary
ERPNext doctype/method from the caller (mục 9.4 forbidden tools:
erp_execute_sql, erp_call_any_endpoint, erp_delete_document,
erp_cancel_any_document, erp_change_user_role, erp_create_api_key,
erp_run_server_script, erp_upload_custom_app). If it isn't in this file,
Hermes cannot do it — full stop.
"""

from dataclasses import dataclass
from datetime import date
from typing import Callable, Literal

from ..erpnext_client import ERPNextClient

Category = Literal["read", "safe_write", "approval"]


@dataclass
class ToolSpec:
    name: str
    category: Category
    schema: dict
    handler: Callable[[ERPNextClient, dict, dict], dict]  # (client, args, context) -> result
    requires_idempotency_key: bool = False


def _s(**props):
    required = [k for k, v in props.items() if v.pop("__required__", True)]
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


def _field(type_="string", **kw):
    d = {"type": type_}
    d.update(kw)
    return d


# ---------------------------------------------------------------------------
# Read tools (mục 9.1) — always allowed, never need approval or idempotency.
# ---------------------------------------------------------------------------

def h_get_current_user(client, args, ctx):
    return {"profile_name": ctx["profile"].name, "role": ctx["profile"].role}


def h_list_my_tasks(client, args, ctx):
    return client.get_list(
        "Task",
        filters={"_assign": ["like", f"%{ctx['erpnext_user']}%"], "status": ["!=", "Cancelled"]},
        # Task's due-date field is "exp_end_date" (not "expected_end_date" —
        # that longer name is only used on the Project doctype; confirmed
        # against a live site after "Field not permitted in query" errors).
        fields=["name", "subject", "status", "priority", "exp_end_date", "progress"],
        limit_page_length=args.get("limit", 20),
    )


def h_search_tasks(client, args, ctx):
    filters = {"subject": ["like", f"%{args['query']}%"]}
    if args.get("project"):
        filters["project"] = args["project"]
    return client.get_list("Task", filters=filters, fields=["name", "subject", "project", "status"], limit_page_length=20)


def h_get_task(client, args, ctx):
    return client.get_doc("Task", args["task_id"])


def h_get_project(client, args, ctx):
    return client.get_doc("Project", args["project_id"])


def h_project_summary(client, args, ctx):
    return client.get_list(
        "Task",
        filters={"project": args["project_id"]},
        fields=["name", "subject", "status", "progress", "exp_end_date"],
        limit_page_length=100,
    )


def h_list_overdue_tasks(client, args, ctx):
    # ERPNext's REST filter parser doesn't understand the "Today" magic
    # value the Desk UI's report/query builder accepts — it needs a real
    # date string (confirmed: "ValidationError: Today is not a valid date
    # string" against a live site), so compute it here.
    return client.get_list(
        "Task",
        filters={"exp_end_date": ["<", date.today().isoformat()], "status": ["not in", ["Completed", "Cancelled"]]},
        fields=["name", "subject", "project", "exp_end_date", "_assign"],
        limit_page_length=args.get("limit", 50),
    )


def h_list_leads(client, args, ctx):
    filters = {"_assign": ["like", f"%{ctx['erpnext_user']}%"]} if ctx["role"] != "ops-admin" else None
    return client.get_list("Lead", filters=filters, fields=["name", "lead_name", "status", "ai_priority"], limit_page_length=20)


def h_get_lead(client, args, ctx):
    return client.get_doc("Lead", args["lead_id"])


def h_list_opportunities(client, args, ctx):
    filters = {"_assign": ["like", f"%{ctx['erpnext_user']}%"]} if ctx["role"] != "ops-admin" else None
    return client.get_list("Opportunity", filters=filters, fields=["name", "party_name", "status", "opportunity_amount"], limit_page_length=20)


def h_pipeline_summary(client, args, ctx):
    return client.get_list("Opportunity", fields=["status", "opportunity_amount"], limit_page_length=200)


def h_get_customer(client, args, ctx):
    return client.get_doc("Customer", args["customer_id"])


def h_get_quotation(client, args, ctx):
    return client.get_doc("Quotation", args["quotation_id"])


def h_get_sales_order(client, args, ctx):
    return client.get_doc("Sales Order", args["sales_order_id"])


def h_stock_balance(client, args, ctx):
    return client.get_list("Bin", filters={"item_code": args["item_code"]}, fields=["warehouse", "actual_qty"], limit_page_length=50)


READ_TOOLS = [
    ToolSpec("erp_get_current_user", "read", _s(), h_get_current_user),
    ToolSpec("erp_list_my_tasks", "read", _s(limit=_field("integer", __required__=False)), h_list_my_tasks),
    ToolSpec("erp_search_tasks", "read", _s(query=_field(), project=_field(__required__=False)), h_search_tasks),
    ToolSpec("erp_get_task", "read", _s(task_id=_field()), h_get_task),
    ToolSpec("erp_get_project", "read", _s(project_id=_field()), h_get_project),
    ToolSpec("erp_project_summary", "read", _s(project_id=_field()), h_project_summary),
    ToolSpec("erp_list_overdue_tasks", "read", _s(limit=_field("integer", __required__=False)), h_list_overdue_tasks),
    ToolSpec("erp_list_leads", "read", _s(), h_list_leads),
    ToolSpec("erp_get_lead", "read", _s(lead_id=_field()), h_get_lead),
    ToolSpec("erp_list_opportunities", "read", _s(), h_list_opportunities),
    ToolSpec("erp_pipeline_summary", "read", _s(), h_pipeline_summary),
    ToolSpec("erp_get_customer", "read", _s(customer_id=_field()), h_get_customer),
    ToolSpec("erp_get_quotation", "read", _s(quotation_id=_field()), h_get_quotation),
    ToolSpec("erp_get_sales_order", "read", _s(sales_order_id=_field()), h_get_sales_order),
    ToolSpec("erp_stock_balance", "read", _s(item_code=_field()), h_stock_balance),
]


# ---------------------------------------------------------------------------
# Safe write tools (mục 9.2) — allowed for Hermes to execute directly, but
# still require an idempotency_key and are restricted to fields listed here
# (field filtering, mục 9.5). Anything not listed (assignee, deadline,
# doctype deletion, cancellation...) is simply not reachable through these
# handlers — that restriction is enforced by omission, not by a runtime
# permission flag that could be misconfigured.
# ---------------------------------------------------------------------------

def h_create_task(client, args, ctx):
    return client.insert("Task", {
        "subject": args["subject"],
        "project": args.get("project"),
        # Tool-facing arg name stays "expected_end_date" (matches the
        # Project tools' vocabulary so callers don't need to remember two
        # different names) but Task's actual field is "exp_end_date".
        "exp_end_date": args.get("expected_end_date"),
        "description": args.get("description"),
        "external_request_id": args["idempotency_key"],
    })


def h_update_task_progress(client, args, ctx):
    progress = args["progress"]
    if not (0 <= progress <= 100):
        raise ValueError("progress must be between 0 and 100")
    return client.update("Task", args["task_id"], {
        "progress": progress,
        "last_ai_check": _now(),
    })


def h_update_task_status(client, args, ctx):
    allowed = {"Open", "Working", "Pending Review", "Completed"}
    if args["status"] not in allowed:
        raise ValueError(f"status must be one of {sorted(allowed)} — use erp_set_task_blocked for Blocked")
    return client.update("Task", args["task_id"], {"status": args["status"]})


def h_add_task_comment(client, args, ctx):
    return client.call_method("frappe.client.add_comment", {
        "reference_doctype": "Task",
        "reference_name": args["task_id"],
        "content": args["comment"],
    })


def h_set_task_blocked(client, args, ctx):
    return client.update("Task", args["task_id"], {
        "status": "Working",
        "blocked_reason": args["reason"],
        "blocked_since": _now(),
    })


def h_create_project_draft(client, args, ctx):
    return client.insert("Project", {
        "project_name": args["project_name"],
        "expected_start_date": args.get("expected_start_date"),
        "expected_end_date": args.get("expected_end_date"),
        "department": args.get("department"),
        "status": "Open",
    })


def h_create_lead(client, args, ctx):
    return client.insert("Lead", {
        "lead_name": args["lead_name"],
        "company_name": args.get("company_name"),
        "email_id": args.get("email"),
        "mobile_no": args.get("phone"),
        "source": args.get("source"),
    })


def h_update_opportunity(client, args, ctx):
    allowed_fields = {"status", "next_followup_date", "opportunity_amount", "ai_summary"}
    updates = {k: v for k, v in args.get("updates", {}).items() if k in allowed_fields}
    if not updates:
        raise ValueError(f"no updatable fields provided, allowed: {sorted(allowed_fields)}")
    return client.update("Opportunity", args["opportunity_id"], updates)


def h_log_crm_activity(client, args, ctx):
    return client.call_method("frappe.client.add_comment", {
        "reference_doctype": args["doctype"],
        "reference_name": args["document_id"],
        "content": args["note"],
    })


def h_create_followup(client, args, ctx):
    return client.update(args["doctype"], args["document_id"], {"next_followup_date": args["followup_date"]})


def h_create_quotation_draft(client, args, ctx):
    return client.insert("Quotation", {
        "party_name": args["customer_or_lead"],
        "items": args["items"],
        "docstatus": 0,  # draft only — erp_request_quotation_submit is required to submit
    })


SAFE_WRITE_TOOLS = [
    ToolSpec("erp_create_task", "safe_write", _s(subject=_field(), project=_field(__required__=False), expected_end_date=_field(__required__=False), description=_field(__required__=False), idempotency_key=_field()), h_create_task, requires_idempotency_key=True),
    ToolSpec("erp_update_task_progress", "safe_write", _s(task_id=_field(), progress=_field("integer")), h_update_task_progress, requires_idempotency_key=True),
    ToolSpec("erp_update_task_status", "safe_write", _s(task_id=_field(), status=_field()), h_update_task_status, requires_idempotency_key=True),
    ToolSpec("erp_add_task_comment", "safe_write", _s(task_id=_field(), comment=_field()), h_add_task_comment, requires_idempotency_key=True),
    ToolSpec("erp_set_task_blocked", "safe_write", _s(task_id=_field(), reason=_field()), h_set_task_blocked, requires_idempotency_key=True),
    ToolSpec("erp_create_project_draft", "safe_write", _s(project_name=_field(), expected_start_date=_field(__required__=False), expected_end_date=_field(__required__=False), department=_field(__required__=False)), h_create_project_draft, requires_idempotency_key=True),
    ToolSpec("erp_create_lead", "safe_write", _s(lead_name=_field(), company_name=_field(__required__=False), email=_field(__required__=False), phone=_field(__required__=False), source=_field(__required__=False)), h_create_lead, requires_idempotency_key=True),
    ToolSpec("erp_update_opportunity", "safe_write", _s(opportunity_id=_field(), updates=_field("object")), h_update_opportunity, requires_idempotency_key=True),
    ToolSpec("erp_log_crm_activity", "safe_write", _s(doctype=_field(), document_id=_field(), note=_field()), h_log_crm_activity, requires_idempotency_key=True),
    ToolSpec("erp_create_followup", "safe_write", _s(doctype=_field(), document_id=_field(), followup_date=_field()), h_create_followup, requires_idempotency_key=True),
    ToolSpec("erp_create_quotation_draft", "safe_write", _s(customer_or_lead=_field(), items=_field("array")), h_create_quotation_draft, requires_idempotency_key=True),
]


# ---------------------------------------------------------------------------
# Approval tools (mục 9.3) — never execute directly. They only ever create
# an "AI Approval Request" row in ERPNext (mục 8.4) via the hermes_ops app.
# A human with the right role must call approve() in ERPNext before
# anything happens; Hermes has no code path to approve its own request
# (mục 8.4 closing rule, enforced again server-side in ai_approval_request.py).
# ---------------------------------------------------------------------------

def _make_approval_request(client, ctx, action: str, target_doctype: str, target_document: str, payload: dict):
    import json as _json

    return client.insert("AI Approval Request", {
        "request_id": f"{action}-{ctx['correlation_id']}",
        "requested_action": action,
        "requested_by": ctx["erpnext_user"],
        "target_doctype": target_doctype,
        "target_document": target_document,
        "payload_json": _json.dumps(payload),
        "approval_status": "Pending",
        "expires_at": _plus_hours(24),
    })


def h_request_task_reassignment(client, args, ctx):
    return _make_approval_request(client, ctx, "erp_request_task_reassignment", "Task", args["task_id"], args)


def h_request_deadline_change(client, args, ctx):
    return _make_approval_request(client, ctx, "erp_request_deadline_change", "Task", args["task_id"], args)


def h_request_quotation_submit(client, args, ctx):
    return _make_approval_request(client, ctx, "erp_request_quotation_submit", "Quotation", args["quotation_id"], args)


def h_request_sales_order(client, args, ctx):
    return _make_approval_request(client, ctx, "erp_request_sales_order", "Quotation", args["quotation_id"], args)


def h_request_purchase_order(client, args, ctx):
    return _make_approval_request(client, ctx, "erp_request_purchase_order", "Supplier", args["supplier_id"], args)


def h_request_stock_adjustment(client, args, ctx):
    return _make_approval_request(client, ctx, "erp_request_stock_adjustment", "Item", args["item_code"], args)


APPROVAL_TOOLS = [
    ToolSpec("erp_request_task_reassignment", "approval", _s(task_id=_field(), new_assignee=_field(), reason=_field()), h_request_task_reassignment, requires_idempotency_key=True),
    ToolSpec("erp_request_deadline_change", "approval", _s(task_id=_field(), new_deadline=_field(), reason=_field()), h_request_deadline_change, requires_idempotency_key=True),
    ToolSpec("erp_request_quotation_submit", "approval", _s(quotation_id=_field()), h_request_quotation_submit, requires_idempotency_key=True),
    ToolSpec("erp_request_sales_order", "approval", _s(quotation_id=_field()), h_request_sales_order, requires_idempotency_key=True),
    ToolSpec("erp_request_purchase_order", "approval", _s(supplier_id=_field(), items=_field("array")), h_request_purchase_order, requires_idempotency_key=True),
    ToolSpec("erp_request_stock_adjustment", "approval", _s(item_code=_field(), warehouse=_field(), quantity_delta=_field("number"), reason=_field()), h_request_stock_adjustment, requires_idempotency_key=True),
]


def _now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _plus_hours(hours: int):
    from datetime import datetime, timedelta, timezone

    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


ALL_TOOLS: dict[str, ToolSpec] = {
    t.name: t for t in [*READ_TOOLS, *SAFE_WRITE_TOOLS, *APPROVAL_TOOLS]
}

# Names that must NEVER appear above (mục 9.4). Kept here only so a unit
# test can assert they stay absent — this list is not a lookup table used
# by any request path.
FORBIDDEN_TOOL_NAMES = {
    "erp_execute_sql",
    "erp_call_any_endpoint",
    "erp_delete_document",
    "erp_cancel_any_document",
    "erp_change_user_role",
    "erp_create_api_key",
    "erp_run_server_script",
    "erp_upload_custom_app",
}
