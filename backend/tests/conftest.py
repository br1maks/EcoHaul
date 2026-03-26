
import asyncio
import os
import pytest
import pytest_asyncio
import psycopg2
from contextlib import asynccontextmanager
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

_TEST_DB_PASSWORD = os.environ.get("TEST_DB_PASSWORD", "postgres")
_TEST_DB_HOST = os.environ.get("TEST_DB_HOST", "127.0.0.1")

TEST_DB = dict(
    host=_TEST_DB_HOST,
    port=5432,
    dbname="ecohaul_test",
    user="postgres",
    password=_TEST_DB_PASSWORD,
)

os.environ["DATABASE_URL"] = (
    f"postgresql+asyncpg://postgres:{_TEST_DB_PASSWORD}@{_TEST_DB_HOST}:5432/ecohaul_test"
)
os.environ["DATABASE_URL_SYNC"] = (
    f"postgresql://postgres:{_TEST_DB_PASSWORD}@{_TEST_DB_HOST}:5432/ecohaul_test"
)
os.environ["DEBUG"] = "True"

def _sync_exec(sql: str):
    conn = psycopg2.connect(**TEST_DB)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.close()

def pytest_configure(config):
    from app.models.base import Base
    from sqlalchemy import create_engine

    _sync_exec("DROP SCHEMA public CASCADE")
    _sync_exec("CREATE SCHEMA public")
    _sync_exec("CREATE EXTENSION IF NOT EXISTS postgis")

    sync_url = os.environ["DATABASE_URL_SYNC"]
    engine = create_engine(sync_url)
    Base.metadata.create_all(engine)
    engine.dispose()

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
def clean_db():
    _sync_exec(
        "TRUNCATE TABLE users, orders, payments, subscriptions, "
        "courier_shifts, addresses, reviews, courier_applications "
        "RESTART IDENTITY CASCADE"
    )
    yield

@pytest_asyncio.fixture
async def client():
    from app.main import app

    @asynccontextmanager
    async def mock_lifespan(app):
        yield

    with patch("app.main.lifespan", mock_lifespan):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
