import asyncio

from app.db.database import Base, engine
from app.models import transcription  # noqa: F401


async def main():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
