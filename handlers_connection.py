"""Connection management for Paychex Flex Connector: connect/disconnect/
list.

Same OAuth2 Client Credentials shape as ADP Workforce Now Connector's
handlers_connection.py, minus the mTLS certificate wrinkle -- connect_paychex
performs the full token exchange synchronously with just client_id/secret.
"""
from __future__ import annotations

import json
import time as _time
import uuid

from imperal_sdk import ActionResult

import paychex_client as pc
from app import chat
from schemas import (
    NoParams,
    ConnectPaychexParams,
    ProviderConnection, ProviderConnectionList,
    DisconnectPaychexParams, DeleteResult,
)

_SECRET_NAME = "paychex_connections"


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_SECRET_NAME)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


async def _save_connections(ctx, connections: list[dict]) -> None:
    await ctx.secrets.set(_SECRET_NAME, json.dumps(connections))


async def resolve_connection(ctx, connection_id: str = "") -> dict | None:
    connections = await _load_connections(ctx)
    if not connections:
        return None
    if connection_id:
        for c in connections:
            if c.get("id") == connection_id:
                return c
        return None
    return connections[0]


async def ensure_fresh_token(ctx, conn: dict) -> dict:
    """Client Credentials tokens have no refresh_token -- re-exchange from
    scratch when within 60s of expiry, using the same stored client_id/secret."""
    expires_at = int(conn.get("expires_at", 0) or 0)
    if expires_at and expires_at - int(_time.time()) > 60:
        return conn
    result = await pc.exchange_client_credentials(ctx, conn.get("client_id", ""), conn.get("client_secret", ""))
    if "access_token" not in result:
        return conn
    conn["access_token"] = result["access_token"]
    conn["expires_at"] = int(_time.time()) + int(result.get("expires_in", 3600))
    connections = await _load_connections(ctx)
    for i, c in enumerate(connections):
        if c.get("id") == conn.get("id"):
            connections[i] = conn
            break
    await _save_connections(ctx, connections)
    return conn


async def resolve_or_error(ctx, connection_id: str = ""):
    conn = await resolve_connection(ctx, connection_id)
    if not conn:
        return None, ActionResult.error(
            "No Paychex Flex connection found. Connect one with connect_paychex first.",
            code="PAYCHEX_NOT_CONNECTED",
        )
    conn = await ensure_fresh_token(ctx, conn)
    return conn, None


@chat.function(
    "connect_paychex",
    "Connect your Paychex Flex company: register your Paychex Developer Partner application's Client ID "
    "and Client Secret from developer.paychex.com. No browser login needed -- the connection is validated "
    "and finished immediately in this one call.",
    action_type="write",
    chain_callable=True,
    data_model=ProviderConnection,
    event="paychex-flex-connector.connect",
    effects=["paychex.connection.created"],
)
async def connect_paychex(ctx, params: ConnectPaychexParams) -> ActionResult:
    """Validate the user's Paychex Developer Partner credentials by
    performing a real Client Credentials token exchange, then save the
    connection if it succeeds."""
    if not params.client_id.strip() or not params.client_secret.strip():
        return ActionResult.error(
            "Client ID and Client Secret are both required.",
            code="PAYCHEX_MISSING_FIELDS",
        )
    result = await pc.exchange_client_credentials(ctx, params.client_id.strip(), params.client_secret.strip())
    if "access_token" not in result:
        return ActionResult.error(
            result.get("message", "Could not connect Paychex -- credentials were rejected."),
            code=result.get("code", "PAYCHEX_UNAUTHORIZED"),
        )
    conn_id = str(uuid.uuid4())
    conn = {
        "id": conn_id,
        "label": params.label.strip() or "Paychex Flex company",
        "client_id": params.client_id.strip(),
        "client_secret": params.client_secret.strip(),
        "access_token": result["access_token"],
        "expires_at": int(_time.time()) + int(result.get("expires_in", 3600)),
        "company_name": "",
    }
    connections = await _load_connections(ctx)
    connections.append(conn)
    await _save_connections(ctx, connections)
    return ActionResult.ok(ProviderConnection(id=conn_id, label=conn["label"], company_name=""))


@chat.function(
    "list_connections",
    "List the connected Paychex Flex companies and whether each saved connection still works.",
    action_type="read", chain_callable=True, data_model=ProviderConnectionList,
)
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """List the connected Paychex Flex companies."""
    connections = await _load_connections(ctx)
    items = [ProviderConnection(id=c.get("id", ""), label=c.get("label", ""), company_name=c.get("company_name", "")) for c in connections]
    return ActionResult.ok(ProviderConnectionList(connections=items))


@chat.function(
    "disconnect_paychex",
    "Disconnect a Paychex Flex company: deletes the saved connection. Nothing in Paychex itself is changed.",
    action_type="destructive", chain_callable=True, data_model=DeleteResult,
    event="paychex-flex-connector.disconnect",
    effects=["paychex.connection.deleted"],
)
async def disconnect_paychex(ctx, params: DisconnectPaychexParams) -> ActionResult:
    """Disconnect a Paychex Flex company: deletes the saved connection."""
    connections = await _load_connections(ctx)
    remaining = [c for c in connections if c.get("id") != params.connection_id]
    if len(remaining) == len(connections):
        return ActionResult.error("Connection not found.", code="PAYCHEX_NOT_CONNECTED")
    await _save_connections(ctx, remaining)
    return ActionResult.ok(DeleteResult(deleted=True, id=params.connection_id))
