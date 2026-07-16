"""One-time provisioning helpers, run via `bench execute` from
playbooks/provision_erpnext.yml — never exposed over HTTP, never callable
by Hermes or the API Bridge. This is deliberately an admin-only, CLI-only
surface (mục 12.3: create dedicated, least-privilege API users).
"""

import frappe
from frappe.core.doctype.user.user import generate_keys


def provision_profile(email: str, full_name: str, role_name: str) -> dict:
    """Create (or reuse) a User for a Hermes profile, assign exactly the
    Hermes role it needs, and issue a fresh API key/secret pair. Returns
    the secret once — the caller (Ansible) is responsible for putting it
    straight into Ansible Vault and not persisting it anywhere else.
    """
    if role_name not in ("Hermes Ops Admin", "Hermes Staff", "Hermes Sales"):
        frappe.throw(f"Refusing to provision unknown role: {role_name}")

    if frappe.db.exists("User", email):
        user = frappe.get_doc("User", email)
    else:
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": full_name,
                "send_welcome_email": 0,
                "user_type": "System User",
            }
        )
        user.insert(ignore_permissions=True)

    # Check/assign the role directly against the child table rather than via
    # user.has_role()/add_roles() — those helper methods aren't present on
    # every Frappe version's User document (confirmed absent on v15.100.1),
    # while appending to the "roles" child table is the stable underlying
    # mechanism both helpers wrap.
    existing_roles = {r.role for r in user.get("roles")}
    if role_name not in existing_roles:
        user.append("roles", {"role": role_name})
        user.save(ignore_permissions=True)

    # Frappe's own key rotation: user.generate_keys() isn't a Document method
    # on this version — the real implementation is the module-level,
    # whitelisted frappe.core.doctype.user.user.generate_keys(user), which
    # sets a new api_secret (and an api_key if one doesn't exist yet) and
    # returns both.
    keys = generate_keys(email)
    frappe.db.commit()

    return {
        "email": email,
        "role": role_name,
        "api_key": keys["api_key"],
        "api_secret": keys["api_secret"],
    }


def _ensure_human_user(email: str, full_name: str, role_name: str):
    """Same idempotent create-or-reuse-user + assign-role logic as
    provision_profile, but for a real human (L1/L2) rather than a shared
    service account: sends a welcome email so they can set their own
    dashboard password, instead of send_welcome_email=0.
    """
    if frappe.db.exists("User", email):
        user = frappe.get_doc("User", email)
    else:
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": full_name,
                "send_welcome_email": 1,
                "user_type": "System User",
            }
        )
        user.insert(ignore_permissions=True)

    existing_roles = {r.role for r in user.get("roles")}
    if role_name not in existing_roles:
        user.append("roles", {"role": role_name})
        user.save(ignore_permissions=True)

    return user


def _set_user_permission(user_email: str, allow: str, for_value: str) -> None:
    """Idempotent: replaces any existing User Permission of this (user,
    allow) pair. A Director/Team Lead should only ever be scoped to exactly
    one Company/Department at a time through this helper — ERPNext's own
    permission engine then auto-filters every list view, report, and API
    call for that user without any application-side filtering code.
    """
    existing = frappe.get_all(
        "User Permission",
        filters={"user": user_email, "allow": allow},
        pluck="name",
    )
    for name in existing:
        frappe.delete_doc("User Permission", name, ignore_permissions=True, force=True)

    frappe.get_doc(
        {
            "doctype": "User Permission",
            "user": user_email,
            "allow": allow,
            "for_value": for_value,
            "apply_to_all_doctypes": 1,
        }
    ).insert(ignore_permissions=True)


def provision_director(email: str, full_name: str, company: str) -> dict:
    """L1 — company director. Real human, dashboard login (mục 6.4). Scoped
    to their own Company via a User Permission row so Project/Task/Employee
    list views and reports are automatically filtered to that Company only.
    Does not issue an API key/secret — Directors act through the shared
    ops-admin bot after /link, the same way staff use staff-work.
    """
    if not frappe.db.exists("Company", company):
        frappe.throw(f"Unknown Company: {company}")

    _ensure_human_user(email, full_name, "Hermes Director")
    _set_user_permission(email, "Company", company)
    frappe.db.commit()

    return {"email": email, "role": "Hermes Director", "company": company}


def provision_team_lead(email: str, full_name: str, department: str) -> dict:
    """L2 — team lead. Real human, dashboard login. Scoped to their own
    Department via a User Permission row — same mechanism as
    provision_director, one level down the hierarchy (mục 6.4).
    """
    if not frappe.db.exists("Department", department):
        frappe.throw(f"Unknown Department: {department}")

    _ensure_human_user(email, full_name, "Hermes Team Lead")
    _set_user_permission(email, "Department", department)
    frappe.db.commit()

    return {"email": email, "role": "Hermes Team Lead", "department": department}
