"""Unit tests need no services; database tests opt in with --integration."""
import asyncio
import os
from urllib.parse import quote

import pytest
import pytest_asyncio

# These values are confined to the test process, before the app is imported.
os.environ['SECRET_KEY'] = 'test-only-secret-key-not-for-production-000000'
os.environ['TELEGRAM_ENABLED'] = 'False'
os.environ['DOCS_ENABLED'] = 'True'
os.environ['DEBUG'] = 'True'
os.environ['ENABLE_DEV_AUTH'] = 'True'
os.environ['PAYMENTS_ENABLED'] = 'True'
password = quote(os.getenv('TEST_DB_PASSWORD', 'postgres'), safe='')
host = os.getenv('TEST_DB_HOST', '127.0.0.1')
port = os.getenv('TEST_DB_PORT', '55432')
os.environ['DATABASE_URL'] = f'postgresql+asyncpg://postgres:{password}@{host}:{port}/ecohaul_test'
os.environ['DATABASE_URL_SYNC'] = f'postgresql+psycopg2://postgres:{password}@{host}:{port}/ecohaul_test'
os.environ['REDIS_URL'] = os.getenv('TEST_REDIS_URL', 'redis://127.0.0.1:56379/0')


def pytest_addoption(parser):
    parser.addoption('--integration', action='store_true', help='Use the disposable ecohaul_test database')


def pytest_configure(config):
    config.addinivalue_line('markers', 'integration: requires PostgreSQL/PostGIS and Redis')


def pytest_collection_modifyitems(config, items):
    if not config.getoption('--integration'):
        for item in items:
            if 'integration' in item.keywords:
                item.add_marker(pytest.mark.skip(reason='Pass --integration to use disposable services'))


@pytest.fixture(scope='session')
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='session')
def database_schema():
    from sqlalchemy import create_engine, text
    from app.models import Base

    engine = create_engine(os.environ['DATABASE_URL_SYNC'])
    # The connection is constructed above with a fixed test database name.
    if engine.url.database != 'ecohaul_test':
        raise RuntimeError('Tests may only reset ecohaul_test')
    with engine.begin() as connection:
        connection.execute(text('DROP SCHEMA public CASCADE'))
        connection.execute(text('CREATE SCHEMA public'))
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS postgis'))
        Base.metadata.create_all(connection)
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_db(request):
    if 'integration' not in request.node.keywords:
        yield
        return
    request.getfixturevalue('database_schema')
    from sqlalchemy import create_engine, text
    from app.models import Base

    engine = create_engine(os.environ['DATABASE_URL_SYNC'])
    with engine.begin() as connection:
        names = ', '.join('"' + table.name + '"' for table in Base.metadata.tables.values())
        connection.execute(text(f'TRUNCATE TABLE {names} RESTART IDENTITY CASCADE'))
    engine.dispose()
    yield


@pytest_asyncio.fixture
async def client():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.core.redis import init_redis, close_redis
    from app.core.database import engine

    await init_redis()
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as session:
        yield session
    await close_redis()
    await engine.dispose()
