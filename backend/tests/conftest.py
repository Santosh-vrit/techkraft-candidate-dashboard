import os
import tempfile

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import database
from app.auth import hash_password
from app.database import Base
from app.main import app
from app.models import Role, User


@pytest_asyncio.fixture
async def client():
    # A real (temp) SQLite file rather than ":memory:" -- an in-memory
    # SQLite DB is scoped to a single connection, and the async engine
    # opens a fresh connection per session, so state wouldn't persist
    # across requests without extra pooling configuration.
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    test_session_local = async_sessionmaker(engine, expire_on_commit=False)

    # Point the app's session factory + candidate_service background tasks at
    # the same in-memory engine used by the test client.
    database.engine = engine
    database.AsyncSessionLocal = test_session_local

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with test_session_local() as session:
            yield session

    app.dependency_overrides[database.get_db] = override_get_db

    async with test_session_local() as session:
        session.add(User(email="admin@techkraft.io", hashed_password=hash_password("admin12345"), role=Role.admin))
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()
    os.remove(path)


async def register_and_login(client: AsyncClient, email: str, password: str = "password123") -> str:
    await client.post("/auth/register", json={"email": email, "password": password, "name": "Test User"})
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


async def admin_login(client: AsyncClient) -> str:
    resp = await client.post("/auth/login", json={"email": "admin@techkraft.io", "password": "admin12345"})
    return resp.json()["access_token"]
