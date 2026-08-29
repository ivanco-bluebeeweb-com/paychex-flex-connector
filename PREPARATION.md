# Paychex Flex Connector -- Preparation (v0.1)

## API surface
Paychex Developer Center (developer.paychex.com), Paychex Flex REST API --
companies, workers, payrolls, time-off/PTO, benefits. Confirmed via
apis.io, developer.paychex.com, and multiple integration guides
(Rollout, Bindbee, api-evangelist) all agreeing on the same shape
(2026-08-29).

## Auth model
OAuth2 **Client Credentials Grant** -- server-to-server, no browser
redirect (same shape as ADP Workforce Now, but WITHOUT the mutual-TLS
certificate requirement -- just client_id + client_secret against
`https://api.paychex.com/auth/oauth/v2/token`). Confirmed from
apis.io/security/paychex-developer and Paychex's own OpenAPI definitions
(single security scheme `oauth2ClientCredentials`).

## Why BYOK
Same reasoning as every other connector here: the user's own Paychex Flex
company/client data lives inside THEIR OWN Paychex account. Access
requires registering as a Paychex Developer Partner (developer.paychex.com
/partner) and requesting production API keys scoped to specific
verbs/endpoints -- this is a per-partner-application registration, not a
shared Imperal-wide credential. Sandbox credentials are issued during
Paychex's own integration review, not via self-serve signup -- documented
explicitly as a known limitation for the user in IDEAL_ONBOARDING.md.

## Token lifetime
Client Credentials tokens are short-lived and simply re-requested from
scratch when expired -- no refresh_token concept, same as ADP.

## Scope for v1
Read-focused: companies, workers/employees, payrolls, time-off requests,
benefits. Write operations (e.g. running payroll) require specific
partner-approved verbs per Paychex's own partner registration process --
out of scope this release, flagged as explicit follow-up.
