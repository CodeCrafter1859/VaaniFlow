from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.routes.transcriptions import router
from app.core.config import get_settings
from app.db.database import engine
from app.utils.http import configure_app


@asynccontextmanager
async def lifespan(app):
    yield
    await engine.dispose()


app = FastAPI(title=get_settings().app_name, version="1.0.0", lifespan=lifespan)
configure_app(app)
app.include_router(router)


@app.get("/health")
async def health():
    return {"data": {"status": "ok", "service": "rest"}}


@app.get("/ready")
async def ready():
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"data": {"status": "ready"}}
