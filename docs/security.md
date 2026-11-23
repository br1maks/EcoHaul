# Security and configuration

## Authentication

Telegram authentication verifies the HMAC-SHA256 signature of `initData`, checks that
`auth_date` is neither expired nor in the future, and requires an embedded user id.
The backend issues an access JWT (30 minutes by default) and a refresh JWT (7 days).
Protected HTTP endpoints reject refresh tokens used as access tokens; role checks
use the current database record. Blocked users lose access to protected HTTP endpoints.

Browser tokens are stored in `sessionStorage`. This limits persistence to the tab but
does not protect them from XSS. A deployment requiring stronger session isolation
should use an HttpOnly cookie flow with CSRF protections and an explicit refresh-token
revocation/rotation design. The current refresh flow does not provide session revocation.

The legacy WebSocket protocol carries a short-lived access token as a query parameter.
Use TLS and keep query strings out of proxy/application logs; the provided Nginx
configuration disables access logging on this endpoint. A one-time WebSocket ticket
would remove bearer tokens from connection URLs.

## Independent switches

| Setting | Default | Effect |
| --- | --- | --- |
| `DEBUG` | `False` | Development behavior; does not enable documentation or dev login by itself |
| `DOCS_ENABLED` | `False` | Exposes `/api/docs`, `/api/redoc`, `/api/openapi.json` |
| `ENABLE_DEV_AUTH` | `False` | Requires `DEBUG=True` as well; permits synthetic users and role selection |
| `TELEGRAM_ENABLED` | `False` | Starts bot polling and enables background Telegram notification delivery |

Never expose a server with `ENABLE_DEV_AUTH=True` to the internet. Dev authentication
is intended for an isolated workstation/test database. Enabling API docs does not
enable test login. The browser does not silently create or sign in as an administrator.

## Secrets

Run `python scripts/setup_local.py` to create `.env` with fresh random local secrets.
The script preserves an existing `.env`. The API refuses to start with a placeholder
or short JWT secret. Real bot tokens, merchant credentials and private user data must
never be committed. Rotate any real credential that has previously been published:
removing it from the latest commit does not remove it from Git history.

Historical sandbox scripts with hardcoded database credentials have been removed
from the current tree. Git history is preserved.

## Payment notifications

YooKassa notifications are checked by fetching the payment through the authenticated
provider API. The handler verifies status, amount, currency and local identifiers,
then locks the local payment row before applying a state change. A duplicate event
cannot grant the same payment twice. It does not rely on a custom
`X-Webhook-Signature` header or on the browser's success redirect.

See the provider's [notification authentication documentation](https://yookassa.ru/developers/using-api/webhooks).
Provider failures return a non-200 response so delivery can be retried.

## Before a real deployment

- Use HTTPS, a controlled origin allowlist, and trusted reverse-proxy configuration.
- Disable dev authentication; configure Telegram separately from debug mode.
- Validate the merchant, country and currency combination. The domain currently prices
  services in BYN; compatibility with a live YooKassa merchant has not been established.
- Add ingress rate limits, refresh-session revocation, backups and monitoring.
- Review the handling and retention of courier verification data.
- Keep one API worker until WebSocket delivery is externalized.

This repository demonstrates the application and its tested paths. It does not claim
an independently audited security posture or a live payment deployment.
