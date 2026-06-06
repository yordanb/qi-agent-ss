from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract, text
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.models import SsRecord, EsicTm

router = APIRouter()

async def _get_user_nama(db: AsyncSession, nrp: str) -> str:
    result = await db.execute(
        select(SsRecord.nama).where(SsRecord.nrp == nrp).limit(1)
    )
    row = result.scalar()
    return row or nrp


async def _get_ss_stats(db: AsyncSession, nrp: str, year: int = None, month: int = None):
    query = select(SsRecord).where(SsRecord.nrp == nrp)
    if year and month:
        query = query.where(
            and_(
                extract("year", SsRecord.tanggal_laporan) == year,
                extract("month", SsRecord.tanggal_laporan) == month,
            )
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
        "outstanding": max(0, outstanding),
        "wait_approval": wait_approval,
        "other": max(0, other),
        "last_update": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
    }


# ─── SS Stats ───────────────────────────────────────────

@router.get("/ss/stats/{nrp}")
async def get_ss_stats(nrp: str, db: AsyncSession = Depends(get_db)):
    nama = await _get_user_nama(db, nrp)

    # Get dept from SS records
    result = await db.execute(
        select(SsRecord.dept).where(SsRecord.nrp == nrp).limit(1)
    )
    dept = result.scalar() or "-"
    stats = await _get_ss_stats(db, nrp)

    return {
        "nrp": nrp,
        "nama": nama,
        "dept": dept,
        **stats,
    }


@router.get("/ss/stats/{nrp}/monthly")
async def get_monthly_stats(
    nrp: str,
    year: int = Query(default=2026),
    month: int = Query(default=6),
    db: AsyncSession = Depends(get_db),
):
    nama = await _get_user_nama(db, nrp)
    result = await db.execute(
        select(SsRecord.dept).where(SsRecord.nrp == nrp).limit(1)
    )
    dept = result.scalar() or "-"
    stats = await _get_ss_stats(db, nrp, year=year, month=month)

    return {
        "nrp": nrp,
        "nama": nama,
        "dept": dept,
        "year": year,
        "month": month,
        **stats,
    }


# ─── SS List ────────────────────────────────────────────

@router.get("/ss/by-nrp/{nrp}")
async def get_ss_by_nrp(
    nrp: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    # Count
    count_sql = text("SELECT COUNT(*) FROM tb_ss.ss_records WHERE nrp = :nrp")
    if status:
        count_sql = text("SELECT COUNT(*) FROM tb_ss.ss_records WHERE nrp = :nrp AND current_status ILIKE :status")
    count_params = {"nrp": nrp, "status": f"%{status}%"}
    count_result = await db.execute(count_sql, count_params)
    total = count_result.scalar()

    # Fetch ordered by tanggal_laporan DESC
    fetch_sql = text("""
        SELECT * FROM tb_ss.ss_records
        WHERE nrp = :nrp
        """ + ("AND current_status ILIKE :status" if status else "") + """
        ORDER BY tanggal_laporan DESC NULLS LAST, created_at DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """)
    fetch_params = {"nrp": nrp, "status": f"%{status}%", "limit": page_size, "offset": (page - 1) * page_size}
    result = await db.execute(fetch_sql, fetch_params)
    records = result.mappings().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [_ss_to_dict(dict(r)) for r in records],
    }


def _ss_to_dict(r) -> dict:
    def val(k, default=None):
        v = r.get(k, default)
        return v if v is not None else default
    return {
        "no_ss": val("no_ss", ""),
        "judul": val("judul", ""),
        "nrp": val("nrp", ""),
        "nama": val("nama") or None,
        "dept": val("dept"),
        "tanggal_laporan": val("tanggal_laporan").isoformat() if val("tanggal_laporan") else None,
        "current_status": val("current_status"),
        "source": val("source"),
        "reward_ss": float(val("reward_ss")) if val("reward_ss") else None,
        "grade_ss": val("grade_ss") or None,
        "created_at": val("created_at").isoformat() if val("created_at") else None,
    }


# ─── ESIC ───────────────────────────────────────────────

@router.get("/esic/by-nrp/{nrp}")
async def get_esic_by_nrp(nrp: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EsicTm).where(EsicTm.nrp == nrp).order_by(EsicTm.snapshot_date.desc())
    )
    snapshots = result.scalars().all()

    return {
        "data": [
            {
                "id": s.id,
                "nrp": s.nrp,
                "nama": s.nama,
                "dept": s.dept,
                "divisi": s.divisi,
                "distrik": s.distrik,
                "posisi": s.posisi,
                "snapshot_date": s.snapshot_date.isoformat() if s.snapshot_date else None,
                "dokumen_diakses": s.dokumen_diakses,
                "dokumen_mtd": s.dokumen_mtd,
                "monthly_metrics": s.monthly_metrics,
            }
            for s in snapshots
        ]
    }


# ─── Dept Dashboard ─────────────────────────────────────

@router.get("/ss/dept/stats/{dept}")
async def get_dept_stats(
    dept: str,
    year: int = Query(default=2026),
    month: int = Query(default=6),
    db: AsyncSession = Depends(get_db),
):
    query = select(SsRecord).where(
        and_(
            SsRecord.dept == dept,
            extract("year", SsRecord.tanggal_laporan) == year,
            extract("month", SsRecord.tanggal_laporan) == month,
        )
    )
    result = await db.execute(query)
    records = result.scalars().all()

    approved = sum(1 for r in records if r.current_status and r.current_status.lower() in ("approved", "closed"))
    waiting = sum(1 for r in records if r.current_status and "wait" in r.current_status.lower())

    return {"dept": dept, "year": year, "month": month, "approved": approved, "waiting": waiting, "total": len(records)}


@router.get("/ss/dept/daily/{dept}")
async def get_dept_daily(
    dept: str,
    year: int = Query(default=2026),
    month: int = Query(default=6),
    db: AsyncSession = Depends(get_db),
):
    query = select(
        extract("day", SsRecord.tanggal_laporan).label("day"),
        func.count().label("count"),
    ).where(
        and_(
            SsRecord.dept == dept,
            extract("year", SsRecord.tanggal_laporan) == year,
            extract("month", SsRecord.tanggal_laporan) == month,
        )
    ).group_by(extract("day", SsRecord.tanggal_laporan)).order_by("day")

    result = await db.execute(query)
    rows = result.all()
    return [{"day": int(row.day), "count": row.count} for row in rows]


# ─── PIN ────────────────────────────────────────────────

@router.get("/upload/pin")
async def generate_pin():
    import random
    pin = str(random.randint(100000, 999999))
    return {"pin": pin, "remaining_seconds": 120}

@router.post("/upload/verify-pin")
async def verify_pin(data: dict):
    pin = data.get("pin", "")
    if len(pin) == 6 and pin.isdigit():
        return {"valid": True}
    return {"valid": False}
