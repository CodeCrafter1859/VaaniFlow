import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test-unused.db"
os.environ["APP_ENV"] = "test"

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.auth import digest
from app.db.database import Base, get_db
from app.main import app
from app.models.transcription import User


@pytest.fixture
async def database(tmp_path):
    url = os.environ.get("TEST_DATABASE_URL")
    schema = "test_" + uuid4().hex
    admin = None
    if url:
        admin = create_async_engine(url)
        async with admin.begin() as connection:
            await connection.execute(text(f"CREATE SCHEMA {schema}"))
        engine = create_async_engine(
            url, poolclass=NullPool, connect_args={"server_settings": {"search_path": schema}}
        )
    else:
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        session.add_all(
            [
                User(name="Alice", token_hash=digest("alice-token")),
                User(name="Bob", token_hash=digest("bob-token")),
            ]
        )
        await session.commit()
    yield factory
    await engine.dispose()
    if admin:
        async with admin.begin() as connection:
            await connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        await admin.dispose()


@pytest.fixture
async def client(database):
    async def override():
        async with database() as db:
            yield db

    app.dependency_overrides[get_db] = override
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer alice-token"},
    ) as client:
        yield client
    app.dependency_overrides.clear()
