"""Onyx Ingest Bridge - the only component allowed to fetch an arbitrary
URL and push it into the Onyx legal/project knowledge base on behalf of a
Hermes profile.

Request flow for POST /ingest_url:
  1. Resolve caller's Hermes profile from the bearer token (auth.py) -
     same per-profile shared-secret pattern as integration/erpnext-bridge.
  2. Rate-limit per profile.
  3. Fetch the URL and extract readable text (fetch.py) - blocks non-http
     schemes and private/internal IPs (SSRF guard).
  4. Push the extracted document to Onyx's Ingestion API, mapped to the
     right Document Set via `target` (legal | project) (onyx_client.py).
  5. Audit-log the outcome (never the Onyx API key, never the full text).
  6. Return a clean error - no stack trace - on any failure so the skill
     can relay something sensible back over Telegram.

Deliberately does not expose any other action. It cannot read ERPNext,
cannot write anywhere except this one Onyx endpoint, and cannot execute
anything found on the fetched page.
"""

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from . import audit
from .auth import resolve_profile
from .config import ProfileConfig, settings
from .fetch import FetchError, fetch_and_extract
from .onyx_client import OnyxError, ingest
from .rate_limit import check_rate_limit

settings.load_profiles()

app = FastAPI(title="Onyx Ingest Bridge", version="0.1.0")


class IngestUrlRequest(BaseModel):
    url: str
    target: str  # "legal" | "project"
    requested_by: str | None = None  # telegram user id/username, audit only


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "profiles_loaded": len(settings.profiles),
        "onyx_base_url": settings.onyx_base_url,
        "cc_pair_legal": settings.cc_pair_legal,
        "cc_pair_project": settings.cc_pair_project,
    }


@app.post("/ingest_url")
def ingest_url(body: IngestUrlRequest, profile: ProfileConfig = Depends(resolve_profile)):
    if body.target not in ("legal", "project"):
        raise HTTPException(status_code=400, detail="target phải là 'legal' hoặc 'project'")

    if not check_rate_limit(profile.name):
        raise HTTPException(status_code=429, detail="Vượt giới hạn tần suất, thử lại sau")

    try:
        title, text = fetch_and_extract(body.url)
    except FetchError as e:
        audit.log_call(profile.name, body.url, body.target, "fetch_failed", str(e))
        raise HTTPException(status_code=422, detail=str(e))

    try:
        result = ingest(title=title, text=text, source_url=body.url, target=body.target)
    except OnyxError as e:
        audit.log_call(profile.name, body.url, body.target, "onyx_failed", str(e))
        raise HTTPException(status_code=502, detail=str(e))
    except ValueError as e:
        audit.log_call(profile.name, body.url, body.target, "config_error", str(e))
        raise HTTPException(status_code=500, detail=str(e))

    audit.log_call(profile.name, body.url, body.target, "ok", f"title={title[:100]}")
    return {
        "title": title,
        "source_url": body.url,
        "target": body.target,
        "document_id": result.get("document_id"),
        "already_existed": result.get("already_existed", False),
        "text_length": len(text),
    }
