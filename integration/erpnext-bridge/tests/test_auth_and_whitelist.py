"""Tests that cannot be waved away: no forbidden tool exists, unknown tools
404, and a profile cannot use another profile's secret."""

from fastapi.testclient import TestClient

from app.main import app
from app.tools.registry import ALL_TOOLS, FORBIDDEN_TOOL_NAMES

client = TestClient(app)


def test_no_forbidden_tool_is_registered():
    registered_names = set(ALL_TOOLS.keys())
    overlap = registered_names & FORBIDDEN_TOOL_NAMES
    assert overlap == set(), f"Forbidden tools must never be registered: {overlap}"


def test_unknown_tool_returns_404():
    resp = client.post(
        "/tools/erp_call_any_endpoint",
        json={"arguments": {}},
        headers={"Authorization": "Bearer ops-secret"},
    )
    assert resp.status_code == 404


def test_missing_bearer_token_is_rejected():
    resp = client.post("/tools/erp_get_current_user", json={"arguments": {}})
    assert resp.status_code == 401


def test_invalid_bearer_token_is_rejected():
    resp = client.post(
        "/tools/erp_get_current_user",
        json={"arguments": {}},
        headers={"Authorization": "Bearer not-a-real-secret"},
    )
    assert resp.status_code == 401


def test_valid_token_resolves_to_correct_profile():
    resp = client.post(
        "/tools/erp_get_current_user",
        json={"arguments": {}},
        headers={"Authorization": "Bearer staff-secret"},
    )
    assert resp.status_code == 200
    assert resp.json()["result"]["role"] == "staff-work"
