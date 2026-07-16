import respx
from fastapi.testclient import TestClient
from httpx import Response

from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer staff-secret"}


def test_missing_required_argument_is_rejected():
    resp = client.post("/tools/erp_get_task", json={"arguments": {}}, headers=AUTH)
    assert resp.status_code == 422
    assert "Invalid arguments" in resp.json()["detail"]


def test_out_of_range_progress_is_rejected_by_handler():
    # No ERPNext mock is registered here on purpose: out-of-range progress
    # must be rejected before the bridge ever calls ERPNext.
    with respx.mock(base_url="http://erpnext-frontend:8080", assert_all_called=False):
        resp = client.post(
            "/tools/erp_update_task_progress",
            json={"arguments": {"task_id": "TASK-0001", "progress": 150}, "idempotency_key": "k1"},
            headers=AUTH,
        )
        assert resp.status_code == 422


def test_write_tool_requires_idempotency_key():
    resp = client.post(
        "/tools/erp_update_task_progress",
        json={"arguments": {"task_id": "TASK-0001", "progress": 50}},
        headers=AUTH,
    )
    assert resp.status_code == 422
    assert "idempotency_key" in resp.json()["detail"]


def test_same_idempotency_key_is_not_executed_twice():
    with respx.mock(base_url="http://erpnext-frontend:8080") as respx_mock:
        route = respx_mock.put("/api/resource/Task/TASK-0002").mock(
            return_value=Response(200, json={"data": {"name": "TASK-0002", "progress": 40}})
        )

        body = {"arguments": {"task_id": "TASK-0002", "progress": 40}, "idempotency_key": "same-key-123"}

        first = client.post("/tools/erp_update_task_progress", json=body, headers=AUTH)
        second = client.post("/tools/erp_update_task_progress", json=body, headers=AUTH)

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["replayed"] is False
        assert second.json()["replayed"] is True
        assert route.call_count == 1, "ERPNext must only be called once for a repeated idempotency key"
