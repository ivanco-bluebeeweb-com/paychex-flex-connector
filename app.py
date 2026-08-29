"""Extension declaration, secrets, lifecycle hooks.

WHY BYOK, same reasoning as every other connector here -- the user's own
Paychex Flex company data lives inside THEIR OWN Paychex account. Imperal
cannot broker a shared Paychex partner registration centrally (requires
Paychex's own Developer Partner approval, developer.paychex.com/partner).

WHY OAUTH2 CLIENT CREDENTIALS, NOT AUTHORIZATION CODE (confirmed from
apis.io/security/paychex-developer + Paychex's own OpenAPI definitions,
2026-08-29): Paychex Flex uses a single security scheme
`oauth2ClientCredentials` -- server-to-server, no browser redirect, no
user consent screen. Simpler than ADP Workforce Now (no mutual TLS
certificate needed here) -- just client_id + client_secret exchanged
directly at the token endpoint.

WHY THERE IS NO REFRESH_TOKEN HANDLING. Client Credentials Grant has no
refresh_token concept -- when the short-lived access_token expires, the
connector simply re-runs the full client-credentials exchange from
scratch.

WHY THIS RELEASE IS READ-FOCUSED. Paychex's write verbs require specific
partner-approved endpoint/verb combinations granted during Paychex's own
Developer Partner review (developer.paychex.com/partner) -- not
universally available to every registered application. v1 scope covers
companies, workers, payrolls, time-off requests, and benefits reads plus
value-add reporting; write operations are flagged as an explicit
follow-up rather than silently omitted.
"""
from __future__ import annotations

from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "paychex-flex-connector",
    version="0.1.0",
    display_name="Paychex Flex",
    icon="icon.svg",
    capabilities=["paychex:read"],
    description=(
        "Connect your own Paychex Flex company (OAuth2 Client Credentials -- bring your own Developer "
        "Partner application Client ID/Secret from developer.paychex.com) to read companies, workers, "
        "payrolls, time-off requests, and benefits, plus value-add workforce reports."
    ),
)

chat = ChatExtension(ext, tool_name="paychex_flex")

ext.secret(
    "paychex_connections", "JSON array of saved Paychex Flex connections (client_id/secret, tokens).",
    required=False, write_mode="extension", max_bytes=65536, rotation_hint_days=365,
)


@ext.health_check
async def health_check(ctx):
    raw = await ctx.secrets.get("paychex_connections")
    return {"ok": True, "has_connections": bool(raw)}
