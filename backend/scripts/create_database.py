"""Create a missing development PostgreSQL database using the configured role."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool


def sqlstate(error):
    """Drivers may expose SQLSTATE directly or through SQLAlchemy's wrapped exception."""
    return getattr(error, "sqlstate", None) or getattr(
        getattr(error, "orig", None), "sqlstate", None
    )


async def ensure_database(target_engine, connect_args=None):
    if target_engine.dialect.name != "postgresql":
        return False
    name = target_engine.url.database
    if not name or "\x00" in name or len(name.encode("utf-8")) > 63:
        raise RuntimeError("DATABASE_URL must name a database of 1 to 63 UTF-8 bytes.")
    try:
        async with target_engine.connect():
            return False
    except Exception as exc:
        if sqlstate(exc) != "3D000":
            raise

    # PostgreSQL forbids CREATE DATABASE inside a transaction. Reuse connection/TLS
    # settings and credentials, changing only the database to the maintenance database.
    maintenance = create_async_engine(
        target_engine.url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
        connect_args=connect_args or {},
    )
    created = False
    try:
        async with maintenance.connect() as connection:
            # Database names are identifiers, not bound values: use dialect quoting,
            # including escaping embedded double quotes, rather than string interpolation.
            identifier = target_engine.dialect.identifier_preparer.quote_identifier(name)
            await connection.execute(text("CREATE DATABASE " + identifier))
            created = True
    except Exception as exc:
        code = sqlstate(exc)
        if code == "42501":
            raise RuntimeError(
                "Database is missing, but the configured PostgreSQL role cannot create it. "
                "Ask an administrator to create it or grant this local role CREATEDB "
                "and CONNECT access to the postgres maintenance database."
            ) from None
        if code not in ("42P04", "23505"):
            raise
        # Another launcher may have created the same database after the initial probe.
        # Reconnect below to verify that the requested database really exists.
    finally:
        await maintenance.dispose()

    async with target_engine.connect():
        pass
    return created
