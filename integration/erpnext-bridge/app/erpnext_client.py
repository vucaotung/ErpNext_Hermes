"""Thin, whitelisted wrapper over the ERPNext REST API.

There is deliberately no generic "call any endpoint" method here (mục 9.4:
erp_call_any_endpoint and erp_execute_sql are forbidden tools and must not
exist anywhere in this codebase, not even as a private helper). Every
method below maps 1:1 to a fixed ERPNext resource + fixed field allowlist.
"""

import httpx

from .config import ProfileConfig, settings


class ERPNextError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class ERPNextClient:
    def __init__(self, profile: ProfileConfig):
        self._profile = profile
        self._client = httpx.Client(
            base_url=settings.erpnext_base_url,
            headers={
                "Authorization": f"token {profile.erpnext_api_key}:{profile.erpnext_api_secret}",
                "Content-Type": "application/json",
            },
            timeout=settings.request_timeout_seconds,
        )

    def get_list(self, doctype: str, filters=None, fields=None, limit_page_length=20):
        params = {"limit_page_length": limit_page_length}
        if filters is not None:
            params["filters"] = _to_json(filters)
        if fields is not None:
            params["fields"] = _to_json(fields)
        return self._request("GET", f"/api/resource/{doctype}", params=params)

    def get_doc(self, doctype: str, name: str):
        return self._request("GET", f"/api/resource/{doctype}/{name}")

    def insert(self, doctype: str, data: dict):
        return self._request("POST", f"/api/resource/{doctype}", json_body=data)

    def update(self, doctype: str, name: str, data: dict):
        return self._request("PUT", f"/api/resource/{doctype}/{name}", json_body=data)

    def call_method(self, dotted_path: str, data: dict):
        """Calls a whitelisted @frappe.whitelist() method by its exact
        dotted path — never a user-supplied string. Only used for the
        handful of controller methods defined in apps/hermes_ops
        (create_link_code, redeem_link_code, approve, reject).
        """
        return self._request("POST", f"/api/method/{dotted_path}", json_body=data)

    def _request(self, method: str, path: str, params=None, json_body=None):
        resp = self._client.request(method, path, params=params, json=json_body)
        if resp.status_code >= 400:
            # Never relay ERPNext's raw traceback to the caller (mục 9.5).
            raise ERPNextError(resp.status_code, _safe_message(resp))
        return resp.json()


def _to_json(value):
    import json

    return json.dumps(value)


def _safe_message(resp) -> str:
    try:
        body = resp.json()
        return body.get("exception") or body.get("message") or f"ERPNext error {resp.status_code}"
    except ValueError:
        return f"ERPNext error {resp.status_code}"
