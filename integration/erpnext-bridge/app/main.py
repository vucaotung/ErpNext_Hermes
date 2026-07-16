"""ERPNext API Bridge — the only component allowed to speak to the ERPNext
REST API on behalf of a Hermes profile (mục 2.3, 9 of the deployment plan).

Request flow for POST /tools/{tool_name}:
  1. Resolve caller's Hermes profile from the bearer token (auth.py).
  2. Look up the tool in the whitelist (tools/registry.py). 404 if unknown
     — there is no fallback to a generic ERPNext call.
  3. Rate-limit per profile.
  4. Validate `arguments` against the tool's JSON Schema.
  5. For write/approval tools, require `idempotency_key`; if seen before
     for this profile, return the cached result without re-executing.
  6. Call the handler with a fresh ERPNextClient scoped to the caller's own
     ERPNext API user (never a shared/admin key).
  7. Audit-log the outcome (never the API secret, never full payload).
  8. Return a clean error (no ERPNext traceback) on failure.
"""

import uuid

from fastapi import Depends, FastAPI, HTTPException
from jsonschema import ValidationError, validate
from pydantic import BaseModel

from .auth import resolve_profile
from .config import ProfileConfig, settings
from .erpnext_client import ERPNextClient, ERPNextError
from .idempotency import get_cached_result, store_result
from .rate_limit import check_rate_limit
from .tools.registry import ALL_TOOLS
from . import audit

settings.load_profiles()

app = FastAPI(title="ERPNext API Bridge", version="0.1.0")


class ToolCallRequest(BaseModel):
    arguments: dict = {}
    idempotency_key: str | None = None
    correlation_id: str | None = None


@app.get("/healthz")
def healthz():
    return {"status": "ok", "profiles_loaded": len(settings.profiles)}


@app.get("/tools")
def list_tools(profile: ProfileConfig = Depends(resolve_profile)):
    """Lets a profile introspect only the tools it's configured to use —
    still every call to /tools/{name} is re-checked independently."""
    return {"tools": [{"name": t.name, "category": t.category, "schema": t.schema} for t in ALL_TOOLS.values()]}


class IdentityLinkRequest(BaseModel):
    code: str
    telegram_user_id: str
    telegram_username: str | None = None


@app.post("/identity/link")
def identity_link(body: IdentityLinkRequest, profile: ProfileConfig = Depends(resolve_profile)):
    """Redeems a one-time /link code generated in ERPNext (Telegram Identity
    Link Code) and creates/activates a Telegram Identity row.

    Deliberately NOT in ALL_TOOLS — the model can never call this. It is
    only ever invoked by the profile's own gateway hook, which is the one
    place that receives the real Telegram user_id straight from Hermes
    (not from the LLM) when a user sends /link <code> (mục 5.5).
    """
    client = ERPNextClient(profile)
    try:
        result = client.call_method(
            "hermes_ops.hermes_ops.doctype.telegram_identity.telegram_identity.redeem_link_code",
            {
                "code": body.code,
                "telegram_user_id": body.telegram_user_id,
                "telegram_username": body.telegram_username,
            },
        )
    except ERPNextError as exc:
        audit.log_call(profile.name, "identity_link", "-", "erpnext_error", exc.message)
        raise HTTPException(status_code=422, detail=exc.message)
    audit.log_call(profile.name, "identity_link", "-", "ok")
    return {"result": result.get("message", result)}


@app.get("/identity/tasks")
def identity_tasks(telegram_user_id: str, profile: ProfileConfig = Depends(resolve_profile)):
    """Resolves telegram_user_id -> the real ERPNext user via this profile's
    Telegram Identity mappings, then lists that person's own tasks. Also
    not an LLM-callable tool — only the /mytasks gateway hook calls this,
    passing the real Telegram user_id it received from Hermes directly.
    """
    client = ERPNextClient(profile)
    identity_rows = client.get_list(
        "Telegram Identity",
        filters={"telegram_user_id": telegram_user_id, "allowed_profile": profile.role, "active": 1},
        fields=["erpnext_user"],
        limit_page_length=1,
    )
    data = identity_rows.get("data", [])
    if not data:
        return {"linked": False}

    erpnext_user = data[0]["erpnext_user"]
    tasks = client.get_list(
        "Task",
        filters={"_assign": ["like", f"%{erpnext_user}%"], "status": ["!=", "Cancelled"]},
        fields=["name", "subject", "status", "priority", "exp_end_date", "progress"],
        limit_page_length=20,
    )
    return {"linked": True, "erpnext_user": erpnext_user, "tasks": tasks.get("data", [])}


def _resolve_caller(client: ERPNextClient, telegram_user_id: str, profile_role: str) -> str | None:
    rows = client.get_list(
        "Telegram Identity",
        filters={"telegram_user_id": telegram_user_id, "allowed_profile": profile_role, "active": 1},
        fields=["erpnext_user"],
        limit_page_length=1,
    ).get("data", [])
    return rows[0]["erpnext_user"] if rows else None


@app.get("/identity/list")
def identity_list(profile: ProfileConfig = Depends(resolve_profile)):
    """Lists every active Telegram Identity linked to THIS profile — used
    only by the profile's own cron scripts (reminders/reports), never by
    the LLM or an MCP tool. Scoped to the calling profile's own role, the
    same isolation boundary every other endpoint here uses.
    """
    client = ERPNextClient(profile)
    rows = client.get_list(
        "Telegram Identity",
        filters={"allowed_profile": profile.role, "active": 1},
        fields=["telegram_user_id", "erpnext_user", "employee", "department"],
        limit_page_length=200,
    )
    return {"identities": rows.get("data", [])}


class AssignTaskRequest(BaseModel):
    telegram_user_id: str
    task_id: str
    assignee_email: str
    note: str | None = None


@app.post("/identity/assign_task")
def identity_assign_task(body: AssignTaskRequest, profile: ProfileConfig = Depends(resolve_profile)):
    """Assigns a Task to assignee_email — but only if the CALLER (resolved
    from their own verified Telegram identity via the /assign gateway hook,
    never from the LLM) actually has the right to: a Hermes Director may
    assign within their own Company, a Hermes Team Lead only within their
    own Department (mục 6.4). The REST call itself still runs under the
    profile's shared service-account credentials — this scope check is
    what enforces the L1/L2 boundary, since the shared account's own
    ERPNext role would otherwise permit touching any Task.
    """
    client = ERPNextClient(profile)

    caller_email = _resolve_caller(client, body.telegram_user_id, profile.role)
    if not caller_email:
        raise HTTPException(status_code=403, detail="Bạn chưa /link tài khoản ERPNext.")

    caller = client.get_doc("User", caller_email)
    caller_roles = {r["role"] for r in caller.get("roles", [])}

    assignee_rows = client.get_list(
        "Employee",
        filters={"user_id": body.assignee_email},
        fields=["company", "department"],
        limit_page_length=1,
    ).get("data", [])
    if not assignee_rows:
        raise HTTPException(status_code=422, detail=f"Không tìm thấy Employee cho {body.assignee_email}")
    assignee = assignee_rows[0]

    if "Hermes Team Lead" in caller_roles:
        perms = client.get_list(
            "User Permission",
            filters={"user": caller_email, "allow": "Department"},
            fields=["for_value"],
            limit_page_length=1,
        ).get("data", [])
        caller_department = perms[0]["for_value"] if perms else None
        if not caller_department or assignee.get("department") != caller_department:
            raise HTTPException(status_code=403, detail="Nhân viên này không thuộc phòng ban của bạn.")
    elif "Hermes Director" in caller_roles:
        perms = client.get_list(
            "User Permission",
            filters={"user": caller_email, "allow": "Company"},
            fields=["for_value"],
            limit_page_length=1,
        ).get("data", [])
        caller_company = perms[0]["for_value"] if perms else None
        if not caller_company or assignee.get("company") != caller_company:
            raise HTTPException(status_code=403, detail="Nhân viên này không thuộc công ty của bạn.")
    else:
        raise HTTPException(status_code=403, detail="Bạn không có quyền giao việc (cần role Hermes Director hoặc Hermes Team Lead).")

    try:
        result = client.call_method(
            "frappe.desk.form.assign_to.add",
            {
                "doctype": "Task",
                "name": body.task_id,
                "assign_to": [body.assignee_email],
                "description": body.note or f"Giao qua Hermes bởi {caller_email}",
            },
        )
    except ERPNextError as exc:
        audit.log_call(profile.name, "identity_assign_task", "-", "erpnext_error", exc.message)
        raise HTTPException(status_code=422, detail=exc.message)

    audit.log_call(profile.name, "identity_assign_task", "-", "ok")
    return {"result": result, "assigned_to": body.assignee_email, "task_id": body.task_id}


@app.get("/identity/scope_report")
def identity_scope_report(telegram_user_id: str, profile: ProfileConfig = Depends(resolve_profile)):
    """Task stats (total/open/working/completed/overdue) across everyone in
    the caller's own scope — their Company if they're a Hermes Director,
    their Department if a Hermes Team Lead. Not an LLM tool — only the
    report_managers.py cron script (--no-agent) calls this, once per
    linked identity, to build the L1/L2 digest (mục 6.4).
    """
    from datetime import date

    client = ERPNextClient(profile)
    caller_email = _resolve_caller(client, telegram_user_id, profile.role)
    if not caller_email:
        return {"linked": False}

    caller = client.get_doc("User", caller_email)
    caller_roles = {r["role"] for r in caller.get("roles", [])}

    if "Hermes Director" in caller_roles:
        scope_type = "Company"
    elif "Hermes Team Lead" in caller_roles:
        scope_type = "Department"
    else:
        return {"linked": True, "erpnext_user": caller_email, "scope": None}

    perms = client.get_list(
        "User Permission",
        filters={"user": caller_email, "allow": scope_type},
        fields=["for_value"],
        limit_page_length=1,
    ).get("data", [])
    if not perms:
        return {"linked": True, "erpnext_user": caller_email, "scope": None}
    scope_value = perms[0]["for_value"]

    employees = client.get_list(
        "Employee",
        filters={scope_type.lower(): scope_value},
        fields=["user_id"],
        limit_page_length=200,
    ).get("data", [])
    emails = [e["user_id"] for e in employees if e.get("user_id")]

    today = date.today().isoformat()
    stats = {"total": 0, "open": 0, "working": 0, "completed": 0, "overdue": 0}
    for email in emails:
        rows = client.get_list(
            "Task",
            filters={"_assign": ["like", f"%{email}%"], "status": ["!=", "Cancelled"]},
            fields=["name", "subject", "status", "exp_end_date"],
            limit_page_length=100,
        ).get("data", [])
        for t in rows:
            stats["total"] += 1
            status = t.get("status")
            if status == "Completed":
                stats["completed"] += 1
            elif status == "Working":
                stats["working"] += 1
            elif status == "Open":
                stats["open"] += 1
            if t.get("exp_end_date") and t["exp_end_date"] < today and status != "Completed":
                stats["overdue"] += 1

    return {
        "linked": True,
        "erpnext_user": caller_email,
        "scope_type": scope_type,
        "scope_value": scope_value,
        "employee_count": len(emails),
        "stats": stats,
    }


@app.post("/tools/{tool_name}")
def call_tool(tool_name: str, body: ToolCallRequest, profile: ProfileConfig = Depends(resolve_profile)):
    correlation_id = body.correlation_id or str(uuid.uuid4())

    tool = ALL_TOOLS.get(tool_name)
    if tool is None:
        audit.log_call(profile.name, tool_name, correlation_id, "rejected", "unknown tool")
        raise HTTPException(status_code=404, detail="Unknown tool")

    if not check_rate_limit(profile.name):
        audit.log_call(profile.name, tool_name, correlation_id, "rate_limited")
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    if tool.requires_idempotency_key and not body.idempotency_key:
        raise HTTPException(status_code=422, detail="idempotency_key is required for this tool")

    try:
        validate(instance=body.arguments, schema=tool.schema)
    except ValidationError as exc:
        audit.log_call(profile.name, tool_name, correlation_id, "invalid_arguments", str(exc.message))
        raise HTTPException(status_code=422, detail=f"Invalid arguments: {exc.message}")

    if tool.requires_idempotency_key:
        cached = get_cached_result(profile.name, body.idempotency_key)
        if cached is not None:
            audit.log_call(profile.name, tool_name, correlation_id, "idempotent_replay")
            return {"result": cached, "correlation_id": correlation_id, "replayed": True}

    client = ERPNextClient(profile)
    context = {
        "profile": profile,
        "role": profile.role,
        # The actual ERPNext username (e.g. "hermes-ops@company.local"), used
        # by tools that filter on "_assign" ("my tasks", "my leads"). ERPNext
        # itself still resolves the calling identity from the API key/secret
        # on every request — this is only for building query filters here.
        "erpnext_user": profile.erpnext_email,
        "correlation_id": correlation_id,
    }

    args = dict(body.arguments)
    if tool.requires_idempotency_key:
        args["idempotency_key"] = body.idempotency_key

    try:
        result = tool.handler(client, args, context)
    except ERPNextError as exc:
        audit.log_call(profile.name, tool_name, correlation_id, "erpnext_error", exc.message)
        raise HTTPException(status_code=502, detail="ERPNext request failed")
    except ValueError as exc:
        audit.log_call(profile.name, tool_name, correlation_id, "validation_error", str(exc))
        raise HTTPException(status_code=422, detail=str(exc))

    if tool.requires_idempotency_key:
        store_result(profile.name, body.idempotency_key, tool_name, result)

    audit.log_call(profile.name, tool_name, correlation_id, "ok")
    return {"result": result, "correlation_id": correlation_id, "replayed": False}
