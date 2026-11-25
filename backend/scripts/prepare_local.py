"""Development-only table initialization and first-user provisioning."""

import argparse
import asyncio
import secrets

from sqlalchemy import select

from app.core.config import get_settings


def validate_config():
    settings = get_settings()
    if settings.app_env != "development":
        raise RuntimeError(
            "run.py is development-only. Use the independent deployment entrypoints in production."
        )
    if "your_password" in settings.database_url:
        raise RuntimeError(
            "Set DATABASE_URL in backend/.env to your real PostgreSQL credentials first."
        )


async def prepare():
    from app.core.auth import digest
    from app.db.database import Base, Session, connect_args, engine
    from app.models.transcription import User
    from scripts.create_database import ensure_database

    try:
        if await ensure_database(engine, connect_args):
            print("Created the PostgreSQL database configured in DATABASE_URL.", flush=True)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with Session() as db:
            settings = get_settings()
            if settings.test_access_token:
                test_user = await db.scalar(
                    select(User).where(User.token_hash == digest(settings.test_access_token))
                )
                if test_user is None:
                    db.add(
                        User(
                            name=settings.test_user_name,
                            token_hash=digest(settings.test_access_token),
                        )
                    )
                    await db.commit()
            if await db.scalar(select(User.id).limit(1)) is None:
                token = secrets.token_urlsafe(32)
                db.add(User(name="Local user", token_hash=digest(token)))
                await db.commit()
                print(f"\nFirst-run login token (save it securely):\n{token}\n", flush=True)
            else:
                print("Database initialized. Sign in with your existing access token.", flush=True)
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-config", action="store_true")
    args = parser.parse_args()
    try:
        validate_config()
        if not args.check_config:
            asyncio.run(prepare())
    except RuntimeError as exc:
        print(str(exc))
        return 1
    except Exception as exc:
        # Never print a database URL or authentication details in launcher diagnostics.
        print(
            f"Database setup failed ({type(exc).__name__}). Ensure PostgreSQL is running, "
            "backend/.env has valid credentials, and the configured role can create a missing database."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
