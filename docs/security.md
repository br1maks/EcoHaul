# Security model

EcoHaul separates three questions: **who sent the request**, **what the current account
may do**, and **whether the requested state change is valid**. A signed token answers
the first question; database-backed authorization and domain checks answer the others.

This document maps those controls to the implementation and its regression tests.
For process boundaries and transaction diagrams, see [architecture](architecture.md).

[Trust boundaries](#1-trust-boundaries-and-protected-assets) ·
[Telegram](#2-telegram-authentication-canonicalization-provenance-and-freshness) ·
[JWT](#3-jwt-lifecycle-and-browser-session-behavior) · [Authorization](#4-authorization-is-role--account-state--object-relationship) ·
[Payments](#6-payment-integrity-and-idempotency) · [WebSockets](#7-websocket-authentication-and-connection-lifetime) ·
[Deployment](#before-a-real-deployment)

## Security controls at a glance

| Boundary | Implemented control | Evidence |
| --- | --- | --- |
| Telegram → API | HMAC verification, bounded launch-data age, required user id | [security helpers](../backend/app/core/security.py), [signature tests](../backend/tests/test_security.py) |
| Browser → protected HTTP API | Pinned JWT algorithm, access/refresh purpose checks, UUID subject validation | [dependencies](../backend/app/api/dependencies.py), [auth routes](../backend/app/api/v1/auth.py) |
| Account → resource | Current database role, active-account checks, owner-scoped queries | [orders](../backend/app/api/v1/orders.py), [addresses](../backend/app/api/v1/addresses.py), [authorization tests](../backend/tests/test_orders.py) |
| Browser → checkout | Server-derived expected amount and order ownership | [checkout](../backend/app/api/v1/payments.py), `test_checkout_rejects_customer_supplied_price` |
| Provider → payment state | Authenticated provider lookup, amount/currency/metadata checks, row lock | [webhook handler](../backend/app/api/v1/payments.py), [webhook tests](../backend/tests/test_webhooks.py) |
| Local tooling → application | Independent development switches, generated secrets, isolated test database | [settings](../backend/app/core/config.py), [setup](../scripts/setup_local.py), [test fixtures](../backend/tests/conftest.py) |

## 1. Trust boundaries and protected assets

The browser, Telegram WebView, request body, URL identifiers and webhook payload are
untrusted input. A hidden button or a TypeScript type is a usability aid, not an access
control. The API makes authorization decisions even when a caller bypasses the UI.

Protected assets include account privileges, pickup addresses and contact information,
order ownership, payment settlement and subscription entitlements. The bot token,
JWT signing key and merchant credentials belong to separate external trust domains.

| Actor / failure | Security question | Enforcement point |
| --- | --- | --- |
| Anonymous caller | Can a fabricated identity obtain a normal authenticated session? | Telegram signature verification or administrator password verification |
| Authenticated client | Can changing an object UUID reveal another client's data? | Owner predicates in queries and order-specific authorization |
| Courier | Can another courier's assigned order be changed? | Current role/verification checks plus the assignment check |
| Checkout caller | Can a cheaper amount be submitted from browser tools? | Expected-price comparison before provider payment creation |
| Forged or repeated callback | Can an entitlement be granted from unverified input or twice? | Provider lookup followed by a locked local state transition |
| Stolen token / compromised browser | How long can the credential be used, and can it be revoked? | Expiration and active-account checks; session-specific revocation remains an extension |

PostgreSQL is the authority for account and business state. Redis caches discovery
results and transports tasks; possessing a cached order does not authorize its acceptance.

## 2. Telegram authentication: canonicalization, provenance and freshness

The API accepts the raw `initData` string and validates it in
[`validate_telegram_init_data`](../backend/app/core/security.py). It does not authenticate
from `initDataUnsafe` or a user id supplied separately by the browser.

The implemented validation sequence is:

1. Parse the URL-encoded key/value pairs and remove the received `hash`.
2. Sort the remaining parsed keys and join `key=value` entries with a newline.
3. Derive a binary key using the bot token and the constant `WebAppData`.
4. Compute the expected HMAC and compare hexadecimal digests using `hmac.compare_digest`.
5. Require `auth_date` within the accepted time window and require an embedded user id.

```text
secret = HMAC-SHA256(key = "WebAppData", message = BOT_TOKEN)
check  = HMAC-SHA256(key = secret, message = canonical_key_value_string)
accept = constant_time_equal(check.hex(), received_hash)
         AND 0 <= utc_now - auth_date <= max_age_seconds
```

The default maximum age is **86,400 seconds**. The lower bound rejects timestamps in
the future; there is no additional clock-skew allowance, so the host clock matters.
A valid launch payload can be reused during this window: freshness bounds replay age,
while a nonce store would be needed for one-time exchange semantics.

A newly discovered Telegram identity is created with the `CLIENT` role. Existing
privileges come from the stored account, rather than Telegram profile fields. The
signature authenticates the launch data; it does not grant an administrator role.

Tests exercise a valid signed payload, tampered user data, expired data, future data
and invalid timestamps. They construct signatures using a test key; they are not a
live Telegram integration test. The protocol reference is
[Telegram's validation guide](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app).

## 3. JWT lifecycle and browser session behavior

### Token contract

| Property | Access token | Refresh token |
| --- | --- | --- |
| Default lifetime | 30 minutes | 7 days |
| Subject | Local user UUID in `sub` | Local user UUID in `sub` |
| Purpose | `type=access` | `type=refresh` |
| Other issued claims | `role`, `iat`, `exp` | `iat`, `exp` |
| Accepted by | Protected HTTP routes and WebSocket handshake | `/auth/refresh` |

[`decode_token`](../backend/app/core/security.py) passes an explicit algorithm allowlist
from server configuration; the default is `HS256`. The token header cannot choose an
arbitrary verification algorithm. Purpose checks in the consumers prevent a refresh
token from being substituted for an access token, or an access token for a refresh token.

Authorization dependencies parse `sub` as a UUID, load the user, and apply current
account/role checks. The `role` claim is not the authority for HTTP permissions.
Consequently, subsequent requests to active-user-protected routes observe account
blocking and role changes without waiting for a new access token.

The refresh endpoint also checks the current account before issuing a token pair.
Issuing a new pair is **not refresh-token rotation**: no token-family record, `jti`
registry or consumed-token state invalidates the previous refresh token. The current
contract also has no explicit issuer/audience binding. These become important when
splitting identity across independently deployed services. See
[JWT validation best practices](https://datatracker.ietf.org/doc/html/rfc8725).

### Browser storage and refresh coordination

[`tokens.ts`](../frontend/src/lib/api/tokens.ts) stores credentials in `sessionStorage`.
They survive reloads in a page session and remain readable by JavaScript; this is not
an HttpOnly or XSS-resistant credential store.

The [Axios interceptor](../frontend/src/lib/api/client.ts) attaches the access token.
Concurrent `401` responses share one refresh promise within that JavaScript instance.
Each failed request is retried once; authentication endpoints are excluded from this
retry path, and failed refresh clears local tokens. This prevents refresh storms and
recursive retries within a tab, not across multiple tabs or devices.

For a stronger browser session boundary, an evolution would combine HttpOnly cookies,
CSRF controls, explicit issuer/audience checks and persisted refresh-session rotation.
Changing storage alone would not implement revocation or prevent malicious same-origin
JavaScript from issuing requests as the user.

## 4. Authorization is role + account state + object relationship

The [dependency chain](../backend/app/api/dependencies.py) is:

```text
Bearer credential → JWT validation → UUID subject → database User
    → active account → required role / courier verification → resource-specific check
```

Examples of the resulting policies:

| Operation | Current policy |
| --- | --- |
| Read/update an address | Query includes address id, current `user_id` and `deleted_at IS NULL` |
| Create an order | Pickup address must belong to the current account and be undeleted |
| Read a payment | Query includes payment id and current `user_id` |
| Accept an order / manage courier shifts | Active, verified courier dependency |
| Advance delivery status | Active admin, or a verified courier assigned to that order |
| Review a delivery | Current user must own the completed order; reviewee must be its courier |
| Administrative endpoints | Current database role must be `ADMIN` |

The order-detail route has a broader discovery policy: courier-role accounts may read
pending orders, or their own assigned orders. That route does not itself use the verified
courier dependency. Address exposure in discovery therefore deserves its own policy
review; it should not be inferred from the stricter acceptance endpoint.

A missing UUID is not automatically returned as the same status on every route: some
owner-scoped lookups return `404`, while order access can explicitly return `403`.
UUIDs reduce accidental enumeration but are not an authorization mechanism.

## 5. Password and verification-code boundaries

Administrator credentials are verified using bcrypt. `bcrypt.gensalt()` provides a
per-hash salt, so equal passwords produce different stored hashes. Tests check both
salt variation and correct/incorrect password verification.

The helper currently truncates UTF-8 password bytes to bcrypt's 72-byte input boundary.
A request limit measured in characters is not equivalent to a byte limit for non-ASCII
passwords. A hardened password policy should reject oversized encoded input or adopt
a versioned hashing migration; the current behavior should not be described as support
for arbitrary-length passwords. In the single-order acceptance endpoint, password
reconfirmation is optional; authenticated courier authorization remains mandatory.

Verification codes use `secrets.choice`, expire after 15 minutes, and are bound to a
user and purpose. The model records usage and attempts. However, the current lookup
includes the submitted code, so a wrong value that matches no row does not consume the
stored attempt counter. That counter is not an account-level brute-force budget.
Code issuance/verification and administrator login require explicit rate controls before
public deployment. These flows should not be represented as a complete MFA system.

## 6. Payment integrity and idempotency

### Price authority

In `POST /payments`, an order payment first resolves an order owned by the current
account. Its expected amount comes from the saved order price; a subscription checkout
uses the server tariff and duration. A mismatched requested amount is rejected before
the provider is called. This is a server-enforced business rule, not a disabled browser
input. Money is stored as `NUMERIC(10,2)`; some request/calculation paths still use floats,
so the current system is not an end-to-end Decimal-only accounting implementation.

### Callback verification sequence

[`yookassa_webhook`](../backend/app/api/v1/payments.py) treats the payload as a notification
to investigate, not proof of settlement:

1. Validate the envelope/event and extract the provider payment id.
2. Fetch that payment through the merchant-authenticated provider API, offloaded with
   `asyncio.to_thread` so the synchronous SDK does not block the event loop in this path.
3. Require the fetched id and status to agree with the handled notification.
4. Lock the matching local payment using `SELECT ... FOR UPDATE`.
5. Compare the provider amount, currency (`BYN`), local payment id and user id in metadata.
6. Apply the terminal state only while the local record is `PENDING`; commit the payment
   and any subscription effect in the database transaction.

The checked metadata comes from the fetched provider object, not the incoming body.
The [provider guide](https://yookassa.ru/developers/using-api/webhooks) describes validating
notifications against current object state. The application does not require a custom
HMAC header or trust the success-page redirect as evidence of payment.

| Condition | Handler behavior |
| --- | --- |
| Invalid JSON or envelope type | `400` |
| Empty payment object | `200` with an error body; no settlement applied |
| Unsupported event | Acknowledged as unhandled, without applying settlement |
| Provider lookup unavailable | `502`, leaving the notification unacknowledged |
| Provider/local identity, status or amount mismatch | `409` |
| Local record already processed | `200`, `already_processed` |
| Unknown local payment id | `200`, `payment_not_found` |

The database lock serializes duplicate callbacks for the **same local payment**. The
provider id also has a unique constraint. For subscription callbacks, a user-row lock
serializes the handler's changes to that user's active subscription.

This is local settlement idempotency, not global exactly-once payment processing.
Checkout does not persist an application idempotency key across repeated create requests.
The provider call and local commit are separate operations: an early callback or a
crash between them can require reconciliation. In particular, an unknown local record
is acknowledged; a recovery process must account for that race. A live merchant/country/
BYN combination has not been verified by the test suite.

## 7. WebSocket authentication and connection lifetime

At `/api/v1/ws`, the handshake validates an access JWT, parses the UUID and requires an
existing active account. `MARK_READ` updates include both notification id and connected
user id. The current protocol exposes no client-originated order mutation messages.

The connection retains the authenticated user id. It does not periodically revalidate
expiration or account blocking, and an established socket is not automatically closed
when an administrator blocks the user. HTTP authorization guarantees must therefore
not be generalized to the whole lifetime of an existing WebSocket connection.

The browser currently sends its bearer token in the connection URL. Nginx access logging
is disabled for this location, but that does not scrub upstream ASGI logs, tracing or
other proxies. A public deployment needs consistent redaction, an explicit WebSocket
Origin policy, and a connection-expiry/revocation strategy. CORS settings alone do not
implement those controls. A short-lived, one-use connection ticket is a cleaner future
protocol than a reusable bearer credential in a URL.

## 8. Configuration, secrets and deployment posture

| Setting | Default | Security meaning |
| --- | --- | --- |
| `DOCS_ENABLED` | `False` | Exposes `/api/docs`, `/api/redoc` and `/api/openapi.json` independently |
| `DEBUG` | `False` | One of two required conditions for development identity endpoints |
| `ENABLE_DEV_AUTH` | `False` | Also requires `DEBUG=True`; synthetic identity/role and test-code paths |
| `TELEGRAM_ENABLED` | `False` | Bot polling and queued Telegram notification delivery |

Never expose the development identity endpoints publicly. They intentionally permit
synthetic identities and role selection. Enabling documentation is not permission to
enable that bypass. The browser has no automatic test-administrator sign-in.

[`setup_local.py`](../scripts/setup_local.py) generates a fresh database password and
64-character hexadecimal JWT secret, preserving an existing `.env`. Startup rejects
short/recognized-placeholder JWT keys; that is a configuration check, not an entropy test.
With one shared signing key, replacing it invalidates outstanding token signatures;
there is no key-ring/overlap mechanism for gradual rotation.

The supplied Compose stack publishes application ports on loopback and keeps PostgreSQL
and Redis internal. The backend runs as a non-root user. Nginx serves HTTP; TLS termination,
rate limits, request/connection size limits, CSP and secret management are deployment
responsibilities rather than protections claimed by the current image.

Treat addresses, contacts and courier verification fields as sensitive. Logs, stored
provider responses, backups and retention policies need the same review as API responses.
Do not commit real bot/merchant credentials or private user records. Rotate a published
credential even after removing it from the latest tree: Git history can retain it.

## 9. Regression evidence and production acceptance criteria

| Evidence | What it demonstrates |
| --- | --- |
| [test_security.py](../backend/tests/test_security.py) | Signature tampering/freshness, token purpose and salted password behavior |
| [test_auth.py](../backend/tests/test_auth.py) | Authentication errors, refresh-purpose rejection and administrator role boundaries |
| [test_orders.py](../backend/tests/test_orders.py) | Cross-client access denial, blocked-user HTTP denial and server price validation |
| [test_webhooks.py](../backend/tests/test_webhooks.py) | Duplicate callback behavior, rejected provider mismatches and provider failure |
| [test_health.py](../backend/tests/test_health.py) | Documentation can be available while development login is disabled |

The tests use real PostgreSQL/PostGIS and Redis for integration paths; provider and
Telegram delivery are controlled doubles. They do not establish live merchant support,
resistance to traffic abuse, a complete XSS/CSRF review or full coverage of every route.

### Before a real deployment

Before a public deployment, acceptance criteria include persisted session revocation,
a bounded login/code attempt budget, password byte-length handling, WebSocket lifetime/
Origin controls, cross-layer log redaction, and payment reconciliation. Each of these
is a separate observable behavior to implement and test, rather than a property inferred
from a successful build or the presence of a security library.
