#!/usr/bin/env python3
"""MCP stdio adapter exposing the ERPNext API Bridge's whitelisted tools to a
Hermes profile over the Model Context Protocol.

Design:
  - The bridge (integration/erpnext-bridge) is a plain REST service, not an
    MCP server. This adapter is the thin translation layer so a native
    Hermes profile can call it as native MCP tools instead of shelling out
    to curl from a skill.
  - Tool list + JSON Schemas are discovered dynamically from GET /tools —
    nothing about the tool catalog is hardcoded here, so adding a tool to
    the bridge's registry.py automatically shows up here on next restart.
  - Every call goes through POST /tools/{name} with a fresh idempotency_key;
    the bridge itself decides whether that key is required or ignored.
  - Auth: one bearer token (= one Hermes profile's shared_secret) per
    adapter instance, via env vars. A profile can never see or use another
    profile's token because each gets its own adapter process.

Env vars required:
  BRIDGE_BASE_URL   e.g. http://127.0.0.1:8642
  BRIDGE_TOKEN      the profile's shared_secret (same value the bridge's
                     PROFILE_<NAME>_SHARED_SECRET vault entry holds)
"""

import asyncio
import json
import os
import sys
import uuid

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

BRIDGE_BASE_URL = os.environ.get("BRIDGE_BASE_URL", "http://127.0.0.1:8642").rstrip("/")
BRIDGE_TOKEN = os.environ.get("BRIDGE_TOKEN", "")

if not BRIDGE_TOKEN:
    print("FATAL: BRIDGE_TOKEN env var not set", file=sys.stderr)
    sys.exit(1)

http_client = httpx.AsyncClient(
    base_url=BRIDGE_BASE_URL,
    headers={"Authorization": f"Bearer {BRIDGE_TOKEN}"},
    timeout=15.0,
)

server = Server("erpnext-bridge")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    resp = await http_client.get("/tools")
    resp.raise_for_status()
    tools = resp.json()["tools"]
    return [
        types.Tool(
            name=t["name"],
            description=f"[{t['category']}] ERPNext tool (via API Bridge)",
            inputSchema=t["schema"],
        )
        for t in tools
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    body = {"arguments": arguments or {}, "idempotency_key": str(uuid.uuid4())}
    try:
        resp = await http_client.post(f"/tools/{name}", json=body)
    except httpx.HTTPError as exc:
        return [types.TextContent(type="text", text=json.dumps({"error": f"bridge unreachable: {exc}"}))]

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = resp.text
        return [types.TextContent(type="text", text=json.dumps({"error": detail, "status": resp.status_code}))]

    return [types.TextContent(type="text", text=json.dumps(resp.json()["result"]))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
