from fastapi import HTTPException
from sqlalchemy import func, or_, select

from app.models.transcription import Transcription


async def create(db, owner_id, values):
    record = Transcription(owner_id=owner_id, **values)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_owned(db, owner_id, record_id):
    record = await db.scalar(
        select(Transcription).where(
            Transcription.id == record_id, Transcription.owner_id == owner_id
        )
    )
    if record is None:
        raise HTTPException(404, "Transcription not found")
    return record


async def listing(
    db,
    owner_id,
    search="",
    language=None,
    status=None,
    sort="created_at",
    order="desc",
    page=1,
    page_size=10,
):
    query = select(Transcription).where(Transcription.owner_id == owner_id)
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(
            or_(
                Transcription.title.ilike(f"%{escaped}%", escape="\\"),
                Transcription.text.ilike(f"%{escaped}%", escape="\\"),
            )
        )
    if language:
        query = query.where(Transcription.language == language)
    if status:
        query = query.where(Transcription.status == status)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    column = getattr(Transcription, sort)
    query = query.order_by(column.desc() if order == "desc" else column.asc(), Transcription.id)
    items = (await db.scalars(query.offset((page - 1) * page_size).limit(page_size))).all()
    return dict(items=items, total=total, page=page, page_size=page_size)


async def stats(db, owner_id):
    base = Transcription.owner_id == owner_id
    groups = (
        await db.execute(
            select(Transcription.status, func.count(), func.sum(Transcription.duration))
            .where(base)
            .group_by(Transcription.status)
        )
    ).all()
    languages = (
        await db.execute(
            select(Transcription.language, func.count())
            .where(base)
            .group_by(Transcription.language)
        )
    ).all()
    return {
        "total": sum(r[1] for r in groups),
        "completed": sum(r[1] for r in groups if r[0] == "completed"),
        "failed": sum(r[1] for r in groups if r[0] == "failed"),
        "duration": sum(r[2] or 0 for r in groups),
        "languages": [{"language": r[0], "count": r[1]} for r in languages],
    }
