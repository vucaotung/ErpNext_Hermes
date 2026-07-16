import os
import sys
import tempfile

# Environment must be set BEFORE app.config / app.main are imported anywhere,
# since Settings() and load_profiles() run once at module import time.
_TMP = tempfile.mkdtemp()

os.environ["ERPNEXT_BASE_URL"] = "http://erpnext-frontend:8080"
os.environ["BRIDGE_PROFILE_NAMES"] = "ops-admin,staff-work"

os.environ["PROFILE_OPS_ADMIN_SHARED_SECRET"] = "ops-secret"
os.environ["PROFILE_OPS_ADMIN_API_KEY"] = "ops-key"
os.environ["PROFILE_OPS_ADMIN_API_SECRET"] = "ops-api-secret"
os.environ["PROFILE_OPS_ADMIN_ROLE"] = "ops-admin"

os.environ["PROFILE_STAFF_WORK_SHARED_SECRET"] = "staff-secret"
os.environ["PROFILE_STAFF_WORK_API_KEY"] = "staff-key"
os.environ["PROFILE_STAFF_WORK_API_SECRET"] = "staff-api-secret"
os.environ["PROFILE_STAFF_WORK_ROLE"] = "staff-work"

os.environ["BRIDGE_IDEMPOTENCY_DB"] = os.path.join(_TMP, "idempotency.sqlite3")
os.environ["BRIDGE_AUDIT_LOG"] = os.path.join(_TMP, "audit.log")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
