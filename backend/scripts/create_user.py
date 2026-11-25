"""Provision a user; the random token is displayed once and only its digest is stored."""

import argparse
import asyncio
import secrets

from app.core.auth import digest
from app.db.database import Session, engine
from app.models.transcription import User


async def main(name):
    token = secrets.token_urlsafe(32)
    async with Session() as db:
        db.add(User(name=name, token_hash=digest(token)))
        await db.commit()
    await engine.dispose()
    print(f"Access token (store securely; shown once): {token}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    asyncio.run(main(parser.parse_args().name))
