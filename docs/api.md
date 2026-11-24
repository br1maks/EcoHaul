# API guide

Base path: `/api/v1`. Interactive docs: `/api/docs` when `DOCS_ENABLED=True`.
The generated [OpenAPI snapshot](api/openapi.json) is the detailed contract.

## Authentication

```http
POST /api/v1/auth/telegram
Content-Type: application/json

{"init_data":"<signed Telegram Mini App launch data>"}
```

Admin sign-in uses `POST /auth/admin/login` with `email` and `password`.
Both flows return `access_token`, `refresh_token` and `token_type`.
Send `Authorization: Bearer <access_token>` on protected endpoints.
Use `POST /auth/refresh` with `{"refresh_token":"..."}` after access expiration.
Refresh rotates the token: store the returned pair atomically and never reuse the old
refresh token. Replay revokes its session family. Session expiry is absolute (7 days by
default); access defaults to 30 minutes. Network failure is distinct from token rejection.

| Session operation | Request / result |
| --- | --- |
| List active sessions | GET /auth/sessions; owned metadata only, including current flag |
| Revoke one | DELETE /auth/sessions/{id}; owned id, 204 |
| Revoke all | POST /auth/logout-all; access authentication, 204 |
| Logout after access expiry | POST /auth/logout with refresh_token JSON; 204 |

Password replacement through PATCH /users/me accepts 15–512 characters and revokes
existing sessions. Application abuse budgets return 429 with Retry-After; see
[security](security.md#4-authorization-is-role--account-state--object-relationship).

## Main endpoint groups

| Group | Examples | Access |
| --- | --- | --- |
| Users | `GET/PATCH /users/me` | Active user |
| Addresses | `GET/POST /addresses` | Owner-scoped |
| Orders | `GET/POST /orders`, `GET /orders/{id}` | Owner / authorized role |
| Courier orders | `/orders/available`, `/orders/my-deliveries`, `POST /orders/{id}/accept` | Verified courier |
| Status | `PATCH /orders/{id}/status` | Assigned verified courier / admin |
| Shifts | `/courier-shifts/start`, `/end`, `/current`, `/history` | Verified courier |
| Applications | `/courier-applications`, `/my`, `/{id}/review` | User / admin review |
| Subscriptions | `/subscriptions/plans`, `/me`, `/purchase` | Public plans / active user |
| Payments | `/payments`, `/{id}` | Owner-scoped |
| Provider callback | `POST /payments/yookassa/webhook` | Confirmed through provider API |
| Admin | `/admin/clients`, `/admin/couriers`, `/admin/statistics/*` | Admin |

List endpoints often return `items`, `total`, `page`, `size`, `pages`; some endpoints,
including notifications, available orders and shift history, return arrays. Refer to
OpenAPI rather than assuming one pagination envelope for every endpoint.

## Create an order

```json
{
  "pickup_address_id": "<an address owned by the client>",
  "garbage_type": "HOUSEHOLD",
  "number_of_bags": 3,
  "scheduled_time": "2027-01-15T10:00:00+03:00",
  "description": "Please call on arrival"
}
```

Choose a future time at least 15 minutes away, during 08:00–21:00 in Minsk.
The server calculates price and discounts. An unaccepted order expires after 30 minutes.

Common errors: 401 invalid/expired authentication; 403 role or ownership denial;
404 missing/inaccessible object; 422 invalid request; 400 invalid domain transition.

## Checkout and recovery

```http
POST /api/v1/payments
Authorization: Bearer <access_token>
Idempotency-Key: <UUID generated once for this purchase intention>
Content-Type: application/json

{"payment_type":"SUBSCRIPTION_PURCHASE","amount":"5.00","subscription_tier":"BASIC","duration_months":1}
```

For order payments use payment_type=ORDER_PAYMENT, order_id and the expected amount;
the owned order must be COMPLETED. POST /subscriptions/purchase accepts tier and
duration_months and requires the same Idempotency-Key header. The server derives prices.

201/202 responses include payment_id, optional payment_url, amount, status,
creation_state and expires_at. 202 means still pending without a URL, with Retry-After: 2.
Retry the exact request/key after network uncertainty; changed input with that key is 409.
Read GET /payments/{id} to inspect the owned durable outcome. A redirect is not proof of
success. REVIEW requires recovery/inspection, not another blind purchase. Admin-only
POST /admin/payments/{id}/reconcile accepts `{}` or a verified-provider identity reference
`{"provider_id":"..."}`. Full [recovery protocol](payments.md).

Payments default to disabled (503). Automatic recurring charging is unsupported (409);
there is no unpaid scheduled extension. Invalid input is 422, conflicting payment state
409, provider verification failure 502 and unknown callback intent 503. Webhook bodies
are independently confirmed through merchant-authenticated provider lookup.

## WebSocket

First request POST /auth/ws-ticket with access authentication. It returns
`{"ticket":"<opaque value>","expires_in":30}`. Connect to
`/api/v1/ws?ticket=<opaque value>` within 30 seconds. The ticket can be consumed once;
reconnect requires a fresh one. Browser Origin must match ALLOWED_ORIGINS. Session
revocation/expiry closes the connection with 1008 (idle checks default to 10 seconds).
The original access deadline also bounds connection lifetime. Durable events use
`{ "event_id": "<stable UUID>", "type": "...", "data": {...} }`; control frames such as
`CONNECTED` and `PONG` do not need an event id. A retry reuses its original event id.
Examples: `CONNECTED`, `NEW_ORDER`, `ORDER_ASSIGNED`, `ORDER_STATUS_CHANGED`,
`NEW_NOTIFICATION`, `SHIFT_ENDED`. Send `PING` for a `PONG`, or `MARK_READ` with a
root-level `notification_id`. Ownership is checked, and read time is persisted.
Assignment/status events carry the persistent inbox id as `data.notification_id`.
After reconnect, reload order state and the inbox through HTTP; the socket is not a replay log.

See [security](security.md) for token/log handling and [architecture](architecture.md)
for the single-worker delivery limitation. [Transactional events](events.md) details
ordering, duplicate handling and operational recovery.
