"""SS repository — DB operations for ss_records and import_log."""
from sqlalchemy import select, func, desc, nulls_last, text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.models import SsRecord, ImportLog, Manpower


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
    closed = sum(1 for r in records if r.source and r.source.lower() == "closed")
    outstanding = sum(1 for r in records if r.source and r.source.lower() == "outstanding")
    other = total - closed - outstanding

    return {
        "total_ss": total,
        "closed": closed,
        "open": max(0, outstanding),
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
    closed = sum(1 for r in records if r.source and r.source.lower() == "closed")
    outstanding = sum(1 for r in records if r.source and r.source.lower() == "outstanding")
    other = total - closed - outstanding

    # Breakdown for "Open" status based on current_status
    status_lower = lambda s: s.lower() if s else ""
    
    open_gl_sh = sum(1 for r in records if r.source and r.source.lower() == "outstanding" and r.current_status and "sh / gl" in status_lower(r.current_status))
    open_dh = sum(1 for r in records if r.source and r.source.lower() == "outstanding" and r.current_status and "dept head" in status_lower(r.current_status))
    open_pm = sum(1 for r in records if r.source and r.source.lower() == "outstanding" and r.current_status and "pm" in status_lower(r.current_status) and "dept head" not in status_lower(r.current_status))
    open_lainnya = max(0, outstanding - open_gl_sh - open_dh - open_pm)

    return {
        "dept": dept,
        "total_ss": total,
        "closed": closed,
        "open": max(0, outstanding),
        "other": max(0, other),
        "breakdown": {
            "open_gl_sh": open_gl_sh,
            "open_dh": open_dh,
            "open_pm": open_pm,
            "open_lainnya": open_lainnya
        }
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


async def get_eiictm_stats(db: AsyncSession, dept: str, year: int = None, month: int = None) -> dict:
    """EIICTM: NRP dari tb_ss.manpower (semua) yg ada/tidak ada judul di ss_records."""
    # Ambil semua NRP dari manpower
    mp_res = await db.execute(text("SELECT nrp FROM tb_ss.manpower"))
    all_nrps = {row[0] for row in mp_res.fetchall()}

    if not all_nrps:
        return {"dept": dept, "total": 0, "have_ss": 0, "no_ss": 0}

    # NRP yang ada di ss_records dengan judul minimal 1
    have_query = select(SsRecord.nrp).where(
        SsRecord.judul != None,
        SsRecord.judul != "",
    )
    if year:
        have_query = have_query.where(func.extract("year", SsRecord.tanggal_laporan) == year)
    if month:
        have_query = have_query.where(func.extract("month", SsRecord.tanggal_laporan) == month)
    have_query = have_query.distinct()

    have_res = await db.execute(have_query)
    have_nrps = {row.nrp for row in have_res.all()}

    have_ss_nrps = all_nrps & have_nrps
    have_ss = len(have_ss_nrps)
    no_ss = len(all_nrps - have_ss_nrps)

    return {
        "dept": dept,
        "total": len(all_nrps),
        "have_ss": have_ss,
        "no_ss": no_ss,
    }
