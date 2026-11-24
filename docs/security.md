# Security model

EcoHaul separates identity, current permissions and valid business transitions. A signed
JWT identifies a session; database checks decide whether that account may act on a
particular resource. This document maps implemented controls to code and tests, with
explicit limits. See [architecture](architecture.md) and [payment recovery](payments.md).

## 1. Trust boundaries and protected assets

Browser input, Telegram launch data, URL ids and callback bodies are untrusted. Protected
assets include privileges, addresses, contact details, payments and subscription access.
Bot, signing and merchant credentials stay on the server.

| Threat | Control | Implementation |
| --- | --- | --- |
| Fabricated Telegram identity | Canonical HMAC verification and freshness bound | [security helpers](../backend/app/core/security.py) |
| Refresh replay | Persisted sessions, rotation and family revocation | [session service](../backend/app/services/sessions.py) |
| Cross-account access | Current role/active state and owner/assignment predicates | [dependencies](../backend/app/api/dependencies.py), [orders](../backend/app/api/v1/orders.py) |
| Password/code guessing | Atomic persistent budgets, cooldown and challenge counters | [limits](../backend/app/services/auth_limits.py), [challenges](../backend/app/services/verification_challenges.py) |
| Duplicate charge or forged settlement | Durable intent, provider key and authenticated verification | [payment lifecycle](../backend/app/services/payment_lifecycle.py) |
| Reused socket credential / foreign Origin | One-use ticket and ongoing session checks | [socket route](../backend/app/websocket/routes.py) |

## 2. Telegram authentication: canonicalization, provenance and freshness

The server removes `hash` from parsed launch data, sorts remaining fields and joins
`key=value` pairs with newlines. It derives an HMAC-SHA256 key from `WebAppData` and the
bot token, calculates the signature and compares with `hmac.compare_digest`. User data
is accepted after signature and timestamp validation; a new Telegram user receives CLIENT.
This follows [Telegram validation](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app).

`auth_date` cannot be in the future or older than `TELEGRAM_AUTH_MAX_AGE_SECONDS`
(default **300 seconds**). This bounds replay; launch data is not single-use. A captured
valid launch can still be exchanged during that window, subject to IP/account budgets.
The frontend reuses an existing session and coalesces concurrent Telegram sign-in calls
instead of creating a new session on every reload. Never log full launch data.

## 3. JWT lifecycle and browser session behavior

JWTs carry `sub`, `sid`, `jti`, `type`, `iss`, `aud`, `iat` and `exp`. Decoding pins the
configured algorithm, issuer and audience, and requires the standard identity/lifetime
claims. HTTP authentication additionally requires a valid UUID subject and a persisted
session owned by that subject. Tokens without `sid` cannot authenticate HTTP requests.
The role claim is informational: permission checks read the current database role.

| Credential | Default lifetime | Persisted state |
| --- | --- | --- |
| Access JWT | 30 minutes | Every protected request checks session ownership, expiry and revocation |
| Refresh JWT | 7 days from initial sign-in | SHA-256 digest of the current signed token; no raw token |
| WebSocket ticket | 30 seconds to connect | Digest, session, original access deadline and consumption time |

Refresh locks User before AuthSession, compares the current token digest, then commits
a new token pair and digest. Rotation retains the original absolute expiry. Reusing a
rotated token **revokes the whole session family**, with the revocation committed before
returning 401. Racing legitimate/attacker refreshes can therefore force a fresh sign-in.
This uses the replay-detection principle in [RFC 9700 section 4.14](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.14);
it is not a claim to implement a complete OAuth authorization server.

Logout accepts the signed refresh token and works after access expiry. Users can list
active sessions, revoke an owned session, or log out everywhere. Password changes and
administrator blocking revoke existing sessions; unblocking does not restore them.
Session issuance, refresh and account-wide revocation serialize on User. Password login
rechecks the verified hash after acquiring the lock, protecting against a concurrent
password change. Already executing business requests are not retroactively rolled back.
Normal rotation leaves the previous access token valid until its expiry unless the
session is subsequently revoked.

The browser uses a shared refresh promise, retries late 401s with an already newer
access token, and prevents delayed refresh from restoring credentials after logout.
Network/503/429 failures preserve credentials for retry; explicit rejection clears them.
Tokens are in sessionStorage: JavaScript in the same origin can read them. XSS prevention,
CSP and dependency review remain necessary. Moving to HttpOnly cookies would require
its own CSRF and deployment design.

## 4. Authorization is role + account state + object relationship

Dependencies load the current account and enforce active state and roles. Handlers then
scope addresses/payments to their owner and order actions to the client, assigned verified
courier or administrator. A UUID is an identifier, not an access-control boundary. Role
changes affect subsequent requests. Domain checks under row locks separately prevent
expired claims, invalid transitions and caller-selected discounts.

### Persistent abuse budgets

PostgreSQL INSERT/ON CONFLICT atomically advances fixed-window counters. Scope/identity
keys are HMAC digests rather than plaintext emails/IPs. Counters commit independently
before rejection, so errors still consume budget. Protected callers release read-only
authentication transactions before reserving this separate budget, avoiding pool starvation
when concurrent requests each need another connection. A regression issues 20 concurrent
ticket requests across the API's 15-connection pool.

| Scope | Budget |
| --- | --- |
| Administrator login | 5/account and 30/source IP per 15 minutes |
| Telegram exchange | 10/verified account and 30/source IP per 15 minutes |
| Code send | 6/account and 3/account+purpose per 15 minutes; 60-second purpose cooldown |
| Code check | 10/account per 15 minutes; at most 3 attempts on latest challenge |
| Checkout | 10/account per minute, including retries |
| Supported payment webhook | 120/source IP per minute before provider lookup |
| Socket ticket | 60/account per minute |

429 responses include Retry-After. These budgets do not provide volumetric DDoS protection.
Configure trusted proxy hops so `request.client.host` reflects the intended source and
untrusted clients cannot forge trusted forwarding headers.

## 5. Passwords and verification codes

New passwords accept **15–512 characters**. New hashes have a `bcrypt_sha256$` prefix:
SHA-256 over the complete UTF-8 input, Base64 encoded, then salted bcrypt. Long Unicode
passwords no longer silently share the same first 72 bytes. Existing bcrypt hashes keep
legacy verification for compatibility and are upgraded on successful administrator login.
Existing weak passwords require user replacement. Admin verification/rehash runs in a
thread; an unknown account still performs a dummy bcrypt comparison. This is an explicit
compatibility format, not an Argon2 implementation.

Random six-digit codes last 15 minutes. Storage uses HMAC-SHA256 bound to challenge id,
user, purpose and code, not plaintext or an unkeyed digest of the small code space.
Verification locks User and the latest challenge by user/purpose **before** comparing
input. Wrong values increment a counter that commits before 401; querying only by the
submitted code would miss those attempts. Concurrent correct submissions consume once.
Resend invalidates previous codes and respects account budgets/cooldown.

Challenge creation and delivery intent commit together. Outbox message text is Fernet
encrypted using a domain-separated key derived from SECRET_KEY. The dispatcher skips
used/expired/superseded challenges before sending. Consumption after that check can race
with transport but cannot make the used code valid again. Domain separation is not
independent key custody: signing-key compromise also compromises derived code protection.

The authenticated challenge API has account_verification, password_reset and 2fa purposes.
Only account verification updates its corresponding flag. The other names do not imply
a complete recovery grant or mandatory MFA login gate. The test-code endpoint requires
both development switches and uses the same budgets.

## 6. Payment integrity and idempotency

Checkout uses server prices, Decimal arithmetic, ownership checks and completed-order
eligibility. A caller UUID Idempotency-Key is unique per user and bound to a canonical
request hash; changed-input reuse returns 409. The immutable intent and separate provider
key commit before any provider creation request.

Callback JSON prompts an authenticated provider lookup. Identity, status, amount, currency
and all frozen metadata are checked before settlement. User then Payment locks serialize
the entitlement update and settlement marker in one transaction. Duplicate success cannot
grant twice; cancellation cannot downgrade settled money. Early callbacks can locate the
committed intent through verified provider metadata. Unknown intent returns 503 for retry.

Scheduled reconciliation covers missed callbacks and uncertain create responses. Retries
reuse the exact payload/key within a conservative 23-hour window; unknown identity beyond
that deadline enters REVIEW rather than creating another charge. Timeout is not proof
of cancellation. Admin recovery also fetches/verifies provider state. See the detailed
[failure matrix and operator procedure](payments.md).

## 7. WebSocket authentication and connection lifetime

An authenticated POST /auth/ws-ticket returns a random ticket; the client opens
`/api/v1/ws?ticket=...`. One conditional database UPDATE consumes it. A reusable JWT no
longer appears in the socket URL. Explicit browser Origin must match ALLOWED_ORIGINS;
a native client without Origin still needs a valid ticket. CORS alone is not this policy.

The route checks session/account before and after each inbound message and while idle
(default WS_AUTH_CHECK_SECONDS=10), shortening the wait to the remaining access lifetime.
Revocation, blocking and expiry close with 1008. An idle socket may remain until the next
check; this is not synchronous global cancellation. Reconnect obtains a fresh ticket.
Do not log ticket query strings: they are sensitive until consumed. One API process is
still required by the local connection registry. Delivery deduplication/recovery is
separate from authentication; see [events](events.md).

## 8. Configuration, secrets and deployment posture

| Setting | Default / effect |
| --- | --- |
| DOCS_ENABLED=False | Documentation exposure independent of development identity |
| DEBUG=False and ENABLE_DEV_AUTH=False | Both required for synthetic identity/role and test-code endpoints |
| TELEGRAM_ENABLED=False | No bot polling or actual Telegram delivery |
| PAYMENTS_ENABLED=False | No external checkout, verification or reconciliation |
| PAYMENT_CURRENCY=BYN | Must match the actual merchant's supported currency and setup |
| JWT_ISSUER=ecohaul, JWT_AUDIENCE=ecohaul-api | Required token provenance values |

[Local setup](../scripts/setup_local.py) generates secrets and preserves an existing .env.
Startup rejects short/recognized placeholder signing keys. Never expose development
identity publicly: it intentionally permits role selection. SECRET_KEY replacement
invalidates JWTs, code digests and queued encrypted code delivery; no overlap key ring
exists. Plan fresh sign-in and challenge reissue.

Compose binds app ports to loopback, keeps DB/Redis internal and runs the backend non-root.
Public TLS, CSP, request/connection limits, proxy trust, backups and restore drills need
deployment configuration. Outbox snapshots may contain personal data; restrict access,
redact logs and apply terminal-row retention. Daily security cleanup removes old buckets
(after one day), tickets (after one hour), and expired/revoked sessions or expired codes
(after 30 days). Pending delivery rows are preserved and need backlog monitoring.

## 9. Regression evidence and production acceptance criteria

| Evidence | Behavior checked |
| --- | --- |
| [security](../backend/tests/test_security.py), [auth](../backend/tests/test_auth.py) | Signature/freshness, token purpose, long-password and legacy compatibility |
| [sessions](../backend/tests/test_sessions.py) | Rotation/replay, owner-only revocation, blocking, atomic budgets, code attempts and tickets |
| [checkout](../backend/tests/test_checkout.py), [webhooks](../backend/tests/test_webhooks.py) | Timeout recovery, early callbacks, concurrent creation, metadata validation and single settlement |
| [REST adapter](../backend/tests/test_payment_adapter.py) | Actual serialization, stable key, timeout configuration and error classification |
| [live transport](../backend/tests/test_live_events.py) | Real HTTP/socket server, bad Origin, ticket replay and active revocation |
| [browser refresh](../frontend/tests/session-refresh.test.mjs), [checkout client](../frontend/tests/checkout.test.mjs) | Concurrent refresh, logout race and retry identity across reload |

Integration paths use real PostgreSQL/PostGIS and Redis with controlled provider/Telegram
responses. They do not establish load capacity, complete route coverage or a full XSS review.

### Before a real deployment

Validate merchant account/currency/country compatibility, provider test-mode payments,
callbacks and recovery. Define refund/dispute procedures and alert on reconciliation lag,
REVIEW rows and outbox backlog. Automatic recurring charges and live merchant acceptance
are not claimed. Review headers, proxy trust, log redaction, personal-data retention,
restore procedures and traffic limits. Measure lock/pool behavior before scaling.
Follow the [migration rollout](development.md#payment-and-session-migration-rollout):
old stateless tokens require fresh sign-in and outstanding plaintext codes are invalidated.
