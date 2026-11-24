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

## WebSocket

Connect to `/api/v1/ws?token=<access_token>`. Durable events use
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
