import hashlib
import secrets
from datetime import timedelta

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.transcription import Ticket, User, utcnow

bearer = HTTPBearer(auto_error=False)


def digest(token: str):
    return hashlib.sha256(token.encode()).hexdigest()


async def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
):
    if not credentials or len(credentials.credentials) > 256:
        raise HTTPException(401, "A valid access token is required")
    user = await db.scalar(select(User).where(User.token_hash == digest(credentials.credentials)))
    if user is None:
        raise HTTPException(401, "A valid access token is required")
    return user


async def issue_ticket(db, owner_id, purpose):
    await db.execute(delete(Ticket).where(Ticket.expires_at < utcnow()))
    token = secrets.token_urlsafe(32)
    db.add(
        Ticket(
            token_hash=digest(token),
            owner_id=owner_id,
            purpose=purpose,
            expires_at=utcnow() + timedelta(seconds=60),
        )
    )
    await db.commit()
    return token


async def consume_ticket(db, token, purpose):
    if not isinstance(token, str) or len(token) > 256:
        raise HTTPException(401, "Invalid ticket")
    result = await db.execute(
        delete(Ticket)
        .where(
            Ticket.token_hash == digest(token),
            Ticket.purpose == purpose,
            Ticket.expires_at > utcnow(),
        )
        .returning(Ticket.owner_id)
    )
    owner = result.scalar_one_or_none()
    await db.commit()
    if owner is None:
        raise HTTPException(401, "Ticket expired or already used")
    return owner
