"""Thin HTTP client for Paychex Flex API + OAuth2 Client Credentials
helper.

Same "fail()-dict + ClientFail exception + generic request() helper"
shape as adp_client.py/gusto_client.py, minus the mTLS wrinkle -- Paychex
uses plain OAuth2 Client Credentials against a single token endpoint.
"""
from __future__ import annotations

from typing import Any

import httpx

TOKEN_URL = "https://api.paychex.com/auth/oauth/v2/token"
API_BASE = "https://api.paychex.com"

PAYCHEX_NOT_CONNECTED = "PAYCHEX_NOT_CONNECTED"
PAYCHEX_UNAUTHORIZED = "PAYCHEX_UNAUTHORIZED"
PAYCHEX_FORBIDDEN = "PAYCHEX_FORBIDDEN"
PAYCHEX_NOT_FOUND = "PAYCHEX_NOT_FOUND"
PAYCHEX_RATE_LIMITED = "PAYCHEX_RATE_LIMITED"
PAYCHEX_BACKEND_ERROR = "PAYCHEX_BACKEND_ERROR"
PAYCHEX_VALIDATION_FAILED = "PAYCHEX_VALIDATION_FAILED"
PAYCHEX_RESPONSE_UNEXPECTED = "PAYCHEX_RESPONSE_UNEXPECTED"

_MESSAGES = {
    PAYCHEX_NOT_CONNECTED: "No Paychex Flex connection found. Connect Paychex first.",
    PAYCHEX_UNAUTHORIZED: "Paychex rejected the request as unauthorized -- the connection may need to be reconnected.",
    PAYCHEX_FORBIDDEN: "Paychex denied access to this resource for the current application's entitlements.",
    PAYCHEX_NOT_FOUND: "That Paychex record was not found.",
    PAYCHEX_RATE_LIMITED: "Paychex rate-limited this request. Try again shortly.",
    PAYCHEX_BACKEND_ERROR: "Paychex's API returned an error.",
    PAYCHEX_VALIDATION_FAILED: "Paychex rejected the request as invalid.",
    PAYCHEX_RESPONSE_UNEXPECTED: "Paychex returned an unexpected response shape.",
}


class ClientFail(Exception):
    def __init__(self, payload: dict):
        self.payload = payload
        super().__init__(payload.get("message", "Paychex request failed"))


def fail(code: str, detail: str = "") -> dict:
    msg = _MESSAGES.get(code, "Paychex request failed.")
    if detail:
        msg = f"{msg} ({detail})"
    return {"error": True, "code": code, "message": msg}


def parse_json_object(raw: str):
    import json
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return False, None
    return isinstance(data, dict), data


async def exchange_client_credentials(ctx, client_id: str, client_secret: str) -> dict:
    """Perform the OAuth2 Client Credentials exchange. Returns a dict with
    access_token/expires_in on success, or a fail()-shaped dict."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
                headers={"Accept": "application/json"},
            )
    except httpx.HTTPError as e:
        return fail(PAYCHEX_BACKEND_ERROR, str(e))
    if resp.status_code == 401:
        return fail(PAYCHEX_UNAUTHORIZED, "invalid client_id/client_secret")
    if resp.status_code >= 400:
        return fail(PAYCHEX_BACKEND_ERROR, f"HTTP {resp.status_code}")
    try:
        data = resp.json()
    except ValueError:
        return fail(PAYCHEX_RESPONSE_UNEXPECTED, "non-JSON token response")
    if "access_token" not in data:
        return fail(PAYCHEX_RESPONSE_UNEXPECTED, "no access_token in response")
    return data


def _headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}


def _check_status(resp: httpx.Response, action: str) -> Any:
    if resp.status_code == 401:
        raise ClientFail(fail(PAYCHEX_UNAUTHORIZED, action))
    if resp.status_code == 403:
        raise ClientFail(fail(PAYCHEX_FORBIDDEN, action))
    if resp.status_code == 404:
        raise ClientFail(fail(PAYCHEX_NOT_FOUND, action))
    if resp.status_code == 429:
        raise ClientFail(fail(PAYCHEX_RATE_LIMITED, action))
    if resp.status_code >= 500:
        raise ClientFail(fail(PAYCHEX_BACKEND_ERROR, f"{action}: HTTP {resp.status_code}"))
    if resp.status_code >= 400:
        raise ClientFail(fail(PAYCHEX_VALIDATION_FAILED, f"{action}: HTTP {resp.status_code}"))
    if resp.status_code == 204 or not resp.content:
        return {}
    try:
        return resp.json()
    except ValueError:
        raise ClientFail(fail(PAYCHEX_RESPONSE_UNEXPECTED, action))


async def request(ctx, conn: dict, method: str, path: str, *, params: dict | None = None,
                   json_body: dict | None = None, action: str = "request") -> Any:
    url = f"{API_BASE}{path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method, url, params=params, json=json_body,
                headers=_headers(conn.get("access_token", "")),
            )
    except httpx.HTTPError as e:
        raise ClientFail(fail(PAYCHEX_BACKEND_ERROR, str(e)))
    return _check_status(resp, action)


def known_entities() -> list[str]:
    return ["companies", "workers", "payrolls", "time-off-requests", "benefits"]


_PATHS = {
    "companies": "/companies/v1/companies",
    "workers": "/companies/v1/companies/{company_id}/workers",
    "payrolls": "/payroll/v1/companies/{company_id}/payrolls",
    "time-off-requests": "/companies/v1/companies/{company_id}/time-off-requests",
    "benefits": "/companies/v1/companies/{company_id}/benefits",
}


def entity_path(entity: str, company_id: str = "") -> str | None:
    tmpl = _PATHS.get(entity)
    if tmpl is None:
        return None
    if "{company_id}" in tmpl:
        if not company_id:
            return None
        return tmpl.format(company_id=company_id)
    return tmpl
