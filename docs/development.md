# Development and testing

## Requirements

- Python 3.11+ and Poetry 2.5.2; the container uses Python 3.11.
- Node.js 22 LTS or later and npm.
- Docker Desktop / Docker Engine with Compose v2.

Both Python and npm dependencies are locked in version control. Use `poetry install`
and `npm ci` for repeatable installs. The SQLAlchemy version is constrained below 2.1
because the current GeoAlchemy2 version depends on the 2.0 table-event API.

## First run with Docker

From the repository root:

```sh
python scripts/setup_local.py
docker compose --env-file .env -f docker/docker-compose.yml up -d --build --wait
```

The migration service initializes PostGIS and applies Alembic migrations before the
API starts. Telegram is disabled by default, so no bot token is needed to inspect the API.

| URL | Purpose |
| --- | --- |
| `http://localhost:8080` | React frontend served by Nginx |
| `http://localhost:8001/api/docs` | Swagger UI, enabled by the local setup script |
| `http://localhost:8001/health` | Real PostgreSQL and Redis readiness; returns 503 on failure |
| `http://localhost:8080/admin/login` | Administrator sign-in |

Create your local administrator:

```sh
docker compose --env-file .env -f docker/docker-compose.yml exec backend python scripts/create_admin.py --email admin@example.test
```

The command prompts for a password. The client-facing flow requires launching the
Mini App from Telegram; the browser explains this when no authenticated session exists.
For Telegram, configure `BOT_TOKEN`, a public HTTPS `WEBAPP_URL`, allowed origins,
and `TELEGRAM_ENABLED=True`. Run one polling bot instance for one bot token.

Useful commands:

```sh
docker compose --env-file .env -f docker/docker-compose.yml ps
docker compose --env-file .env -f docker/docker-compose.yml logs --tail=100 backend
docker compose --env-file .env -f docker/docker-compose.yml down
```

`down` preserves named volumes. Do not add `-v` unless you intend to remove local data.

## Run source code locally

Start PostgreSQL/PostGIS and Redis first. Set database URLs and Redis in the root
`.env` to the host/ports of those services. From `backend`:

```sh
poetry install --no-root
poetry run uvicorn app.main:app --reload --port 8001 --env-file ../.env
```

From `frontend`, in a second terminal:

```sh
npm ci
npm run dev
```

Vite forwards `/api` HTTP and WebSocket traffic to port 8001. Optional frontend
overrides are `VITE_API_URL` (origin without `/api/v1`) and `VITE_WS_URL` (full WS URL).
No secrets belong in `VITE_*` variables: their values are embedded in the browser build.

## Unit tests: no external services

From `backend`:

```sh
poetry run pytest -q
```

Integration tests are explicitly skipped in this mode. Unit tests cover Telegram
signature tampering, expired/future launch data, JWT purposes, password hashing,
readiness failures, and the separation between API docs and development login.

## PostgreSQL / Redis integration tests

From the repository root:

```sh
docker compose -p ecohaul-test -f docker/compose.test.yml up -d --wait
cd backend
poetry run pytest --integration -q
```

The dedicated database is named **ecohaul_test**, on port **55432**; test Redis uses
**56379**. Tests reset only the fixed test database. Never point tests at a database
with user data. Override `TEST_DB_HOST`, `TEST_DB_PORT`, `TEST_DB_PASSWORD` and
`TEST_REDIS_URL` for CI; the workflow uses isolated job services.

Integration coverage includes authentication, role boundaries, blocked users, address
ownership, order transitions, expiration, concurrent courier acceptance and checkout
amount validation. External Telegram delivery is mocked; database transactions and
Redis are real. No payment is sent to a live merchant by the test suite.

Afterwards, from the repository root:

```sh
docker compose -p ecohaul-test -f docker/compose.test.yml down
```

## Frontend checks

```sh
cd frontend
npm run lint -- --max-warnings 0
npm run build
npm audit --omit=dev --audit-level=high
```

## API contract and database changes

```sh
poetry -C backend run python scripts/export_openapi.py
```

OpenAPI is generated from the application; [the checked-in snapshot](api/openapi.json)
can be inspected without running services. Keep it updated after changing a route/schema.
Alembic migrations are checked against a fresh PostGIS database in CI.

## Synthetic demonstration data

`scripts/seed_demo.py` only accepts a database named `ecohaul_demo`, refuses a nonempty
database, and requires Telegram and dev authentication to be disabled. Apply migrations
to that database, then run it with that database configured in the process environment:

```sh
poetry -C backend run python scripts/seed_demo.py
```

It prompts for a demo admin password and creates only fictional users and example orders.
The admin email is `admin@example.test`. It does not import data from any other project.
