"""SS repository — DB operations for ss_records and import_log."""
from sqlalchemy import select, func, desc, nulls_last
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.models import SsRecord, ImportLog


async def get_ss_stats(db: AsyncSession, nrp: str, year: int = None, month: int = None) -> dict:
    query = select(SsRecord).where(SsRecord.nrp == nrp)
    if year and month:
        query = query.where(
            func.extract("year", SsRecord.tanggal_laporan) == year,
            func.extract("month", SsRecord.tanggal_laporan) == month,
        )
    result = await db.execute(query)
    records = result.scalars().all()

    total = len(records)
    closed = sum(1 for r in records if r.current_status and r.current_status.lower() in ("approved", "closed"))
    outstanding = sum(1 for r in records if r.current_status and "outstanding" in r.current_status.lower())
    wait_approval = sum(1 for r in records if r.current_status and "wait" in r.current_status.lower())
    other = total - closed - outstanding - wait_approval

    return {
        "total_ss": total,
        "closed": closed,
        "open": max(0, outstanding + wait_approval),
        "other": max(0, other),
    }


async def get_ss_list(
    db: AsyncSession,
    nrp: str,
    page: int = 1,
    page_size: int = 50,
    status: Optional[str] = None,
) -> dict:
    query = select(SsRecord).where(SsRecord.nrp == nrp)
    if status:
        query = query.where(SsRecord.current_status.ilike(f"%{status}%"))

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    query = query.order_by(
        nulls_last(desc(SsRecord.tanggal_laporan)),
        desc(SsRecord.created_at),
    ).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    records = result.scalars().all()

    return {"total": total, "page": page, "page_size": page_size, "data": records}


async def get_dept_stats(db: AsyncSession, dept: str, year: int = None, month: int = None) -> dict:
    query = select(SsRecord).where(SsRecord.dept == dept)
    if year and month:
        query = query.where(
            func.extract("year", SsRecord.tanggal_laporan) == year,
            func.extract("month", SsRecord.tanggal_laporan) == month,
        )
    result = await db.execute(query)
    records = result.scalars().all()

    total = len(records)
    closed = sum(1 for r in records if r.current_status and r.current_status.lower() in ("approved", "closed"))
    outstanding = sum(1 for r in records if r.current_status and "outstanding" in r.current_status.lower())
    wait_approval = sum(1 for r in records if r.current_status and "wait" in r.current_status.lower())
    other = total - closed - outstanding - wait_approval

    return {
        "dept": dept,
        "total_ss": total,
        "closed": closed,
        "open": max(0, outstanding + wait_approval),
        "other": max(0, other),
    }


async def get_dept_daily(db: AsyncSession, dept: str, year: int, month: int) -> list:
    query = select(
        func.extract("day", SsRecord.tanggal_laporan).label("day"),
        func.count().label("count"),
    ).where(
        SsRecord.dept == dept,
        func.extract("year", SsRecord.tanggal_laporan) == year,
        func.extract("month", SsRecord.tanggal_laporan) == month,
    ).group_by("day").order_by("day")

    result = await db.execute(query)
    return [{"day": int(row.day), "count": row.count} for row in result.mappings()]


async def get_last_import_time(db: AsyncSession):
    result = await db.execute(select(func.max(ImportLog.imported_at)))
    return result.scalar()
