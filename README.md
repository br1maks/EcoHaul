# EcoHaul

A full-stack waste collection service built as a Telegram Mini App. Clients request garbage pickup, couriers accept and complete orders in real time, admins manage the platform through a dedicated web interface.

## Overview

EcoHaul is a marketplace connecting residents with couriers for on-demand garbage removal. The platform handles the full order lifecycle — from address validation and pricing to payment processing, real-time delivery tracking, and post-order reviews.

The application runs as a Telegram Mini App, meaning clients interact entirely through Telegram's embedded WebView. Couriers and admins use the same React frontend but with role-specific interfaces.

## Tech Stack

**Backend**
- Python 3.11, FastAPI, SQLAlchemy (async), asyncpg
- PostgreSQL 16 + PostGIS (geospatial queries)
- Redis — Celery broker and result backend
- Celery + Celery Beat — background tasks and scheduled jobs
- aiogram 3 — Telegram bot and notifications
- Alembic — database migrations
- JWT (access + refresh tokens), Telegram initData HMAC validation

**Frontend**
- React 18, TypeScript, Vite
- Tailwind CSS
- Zustand (state management)
- React Router v6
- Axios with JWT interceptor and auto-refresh

**Infrastructure**
- Docker Compose (6 services)
- Nginx — static file serving and reverse proxy
- Multi-stage Docker builds

## Architecture

```
┌─────────────────────────────────────────────┐
│              Telegram Mini App               │
│         (React + TypeScript + Vite)          │
└──────────────────┬──────────────────────────┘
                   │ HTTP / WebSocket
┌──────────────────▼──────────────────────────┐
│              Nginx (port 80)                 │
│   /api/* → backend:8001                     │
│   /* → React SPA (index.html)               │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│           FastAPI (port 8001)                │
│  REST API + WebSocket (/api/v1/ws)          │
└────┬──────────────┬───────────────┬─────────┘
     │              │               │
┌────▼────┐  ┌──────▼──────┐  ┌───▼───────┐
│Postgres │  │    Redis     │  │  aiogram  │
│+PostGIS │  │(broker+cache)│  │ Telegram  │
└─────────┘  └──────┬───────┘  └───────────┘
                    │
         ┌──────────▼──────────┐
         │  Celery Worker      │
         │  Celery Beat        │
         └─────────────────────┘
```

## Key Features

**Order lifecycle**

Orders move through a defined state machine: `PENDING → ASSIGNED → IN_PROGRESS → ARRIVED → COMPLETED`. Each transition triggers notifications via WebSocket and Telegram simultaneously. Orders that go unaccepted for 30 minutes are automatically cancelled by a scheduled Celery task.

**Real-time delivery tracking**

Clients and couriers communicate through a persistent WebSocket connection (`/api/v1/ws`). New orders are broadcast to all verified online couriers instantly. Status changes are pushed to the relevant client in real time without polling.

**Courier matching queue**

When an order is created, the system creates `OrderQueue` records for available couriers. Each offer has a 60-second expiration. Couriers that decline provide a reason (distance, weight, etc.), which is logged. If no courier accepts within 30 minutes, the order auto-cancels.

**Subscription system**

Three tiers: FREE, BASIC (20% discount), PREMIUM (30% discount). Subscriptions integrate with YooKassa for one-time and recurring payments. Auto-renewal saves a payment method on the first transaction and charges it automatically on the next billing date.

**Geospatial validation**

Service availability is validated against a phase-based zone system. Phase 1 covers specific streets in Minsk. Address coordinates are stored as PostGIS POINT geometry with GiST indexes for fast spatial queries. Street names are validated against an allowlist before an order can be placed.

**Role-based access**

| Role | Access |
|------|--------|
| CLIENT | Create orders, manage addresses, buy subscriptions, rate couriers |
| COURIER | Accept orders, manage shifts, update delivery status (requires phone verification) |
| ADMIN | Full platform management — users, orders, payments, analytics, courier verification |

**Background jobs (Celery Beat)**

- Every 5 minutes: auto-cancel expired unaccepted orders
- Every hour: deactivate expired subscriptions and notify users

**Telegram notifications**

Celery tasks send Telegram messages on key events: order placed, courier assigned, order completed, application approved/rejected, subscription expiring. Tasks retry up to 3 times with a 60-second delay on failure.

## Project Structure

```
EcoHaul/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Route handlers (orders, auth, users, admin, ...)
│   │   ├── core/            # Config, database, security, Redis
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Payment providers, verification
│   │   ├── tasks/           # Celery tasks (notifications, orders, subscriptions)
│   │   ├── telegram/        # aiogram bot and handlers
│   │   └── websocket/       # WebSocket connection manager and routes
│   ├── migrations/          # Alembic migration files
│   ├── tests/               # pytest test suite
│   ├── scripts/             # Dev utilities
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── pages/           # client/, courier/, admin/
│   │   ├── contexts/        # AuthContext (Telegram auth flow)
│   │   ├── shared/          # Components, hooks, types
│   │   ├── lib/api/         # Axios API clients per domain
│   │   └── store/           # Zustand stores
│   └── vite.config.ts
└── docker/
    ├── docker-compose.yml
    ├── Dockerfile.backend
    ├── Dockerfile.frontend
    └── nginx.conf
```

## Running with Docker

**1. Clone the repository**

```bash
git clone https://github.com/br1maks/EcoHaul.git
cd EcoHaul
```

**2. Configure environment**

```bash
cp .env.example .env
```

Edit `.env` and fill in the required values (database password, secret key, Telegram bot token, YooKassa credentials).

**3. Build and start**

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

**4. Run database migrations**

```bash
docker compose -f docker/docker-compose.yml exec backend alembic upgrade head
```

**5. Verify**

```bash
curl http://localhost:8001/health
# {"status":"healthy","database":"connected","phase":1}
```

The API is available at `http://localhost:8001`, the frontend at `http://localhost`.

## Running Locally (Development)

**Backend**

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install poetry && poetry install
uvicorn app.main:app --reload --port 8001
```

**Celery worker** (in a separate terminal)

```bash
cd backend && source venv/bin/activate
celery -A app.celery_app worker --loglevel=info
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` requests to `http://localhost:8001`, so no CORS configuration is needed during development.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `DATABASE_URL` | Async DB URL (`postgresql+asyncpg://...`) |
| `DATABASE_URL_SYNC` | Sync DB URL for Alembic migrations |
| `SECRET_KEY` | JWT signing key (`openssl rand -hex 32`) |
| `BOT_TOKEN` | Telegram bot token |
| `WEBAPP_URL` | Public URL for the Mini App |
| `YOOKASSA_SHOP_ID` | YooKassa shop identifier |
| `YOOKASSA_SECRET_KEY` | YooKassa secret key |
| `REDIS_URL` | Redis connection URL |

See `.env.example` for the full list.

## API Overview

The REST API is versioned under `/api/v1`. All authenticated endpoints require a Bearer token.

| Domain | Base path |
|--------|-----------|
| Auth | `/api/v1/auth` |
| Users | `/api/v1/users` |
| Orders | `/api/v1/orders` |
| Addresses | `/api/v1/addresses` |
| Subscriptions | `/api/v1/subscriptions` |
| Payments | `/api/v1/payments` |
| Courier shifts | `/api/v1/courier-shifts` |
| Courier applications | `/api/v1/courier-applications` |
| Reviews | `/api/v1/reviews` |
| Notifications | `/api/v1/notifications` |
| Service zones | `/api/v1/service-zones` |
| Admin | `/api/v1/admin` |
| WebSocket | `/api/v1/ws` |

Interactive API documentation is available at `http://localhost:8001/docs` when the backend is running.

## Authentication

Clients authenticate via Telegram's initData mechanism. The backend validates the HMAC-SHA256 signature of the Mini App launch parameters against the bot token — no passwords or OAuth flows for regular users.

Admins authenticate with email and password through a separate endpoint.

Both flows issue short-lived JWT access tokens (15 minutes) and long-lived refresh tokens (7 days). The frontend automatically refreshes access tokens on 401 responses.

## Tests

```bash
cd backend
pytest tests/ -v
```

The test suite uses a dedicated PostgreSQL database (`ecohaul_test`) and requires `TEST_DB_PASSWORD` and optionally `TEST_DB_HOST` to be set. The database schema is recreated before each test session; individual tables are truncated between tests.
