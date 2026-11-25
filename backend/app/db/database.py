import ssl
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {}
if settings.database_url.startswith("postgresql"):
    connect_args = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__stt_{uuid4().hex}__",
    }
    if settings.database_ssl:
        connect_args["ssl"] = ssl.create_default_context()
engine = create_async_engine(settings.database_url, poolclass=NullPool, connect_args=connect_args)
Session = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    async with Session() as session:
        yield session
