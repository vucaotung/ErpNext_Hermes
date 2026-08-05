"""Talks to Onyx's Ingestion API (/api/onyx-api/ingestion). Single
responsibility: turn (title, text, source_url, cc_pair_id) into a document
Onyx will index. Document id is a stable hash of the URL so re-ingesting
the same link updates the existing doc instead of creating a duplicate -
Onyx's own ingestion endpoint is upsert-by-id (returns already_existed).
"""

import hashlib

import httpx

from .config import settings


class OnyxError(Exception):
    pass


def _doc_id_for(url: str) -> str:
    return "hermes_" + hashlib.sha256(url.encode()).hexdigest()[:24]


def ingest(title: str, text: str, source_url: str, target: str) -> dict:
    cc_pair_id = settings.cc_pair_for(target)
    payload = {
        "document": {
            "id": _doc_id_for(source_url),
            "semantic_identifier": title[:200],
            "sections": [{"text": text, "link": source_url}],
            "source": "web",
            "metadata": {"ingested_by": "hermes-onyx-bridge"},
        },
        "cc_pair_id": cc_pair_id,
    }
    try:
        resp = httpx.post(
            f"{settings.onyx_base_url}/api/onyx-api/ingestion",
            headers={
                "Authorization": f"Bearer {settings.onyx_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=settings.request_timeout_seconds,
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise OnyxError(f"Onyx từ chối hoặc không phản hồi: {e}") from e

    return resp.json()
