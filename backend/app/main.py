from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.auth import hash_password
from app.config import settings
from app.database import AsyncSessionLocal, Base, engine
from app.models import Role, User
from app.routers import auth as auth_router
from app.routers import candidates as candidates_router


async def seed_admin() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == settings.admin_email))
        if result.scalar_one_or_none() is None:
            admin = User(
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_password),
                role=Role.admin,
            )
            db.add(admin)
            await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_admin()
    yield


app = FastAPI(title="TechKraft Candidate Review API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(candidates_router.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
