from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract
from typing import Optional
from datetime import datetime, timezone, timedelta

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import SsRecord, EsicTm, Manpower, ImportLog

router = APIRouter()

async def _get_user_nama(db: AsyncSession, nrp: str) -> str:
    result = await db.execute(
        select(Manpower.nama).where(Manpower.nrp == nrp).limit(1)
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

    # Get last imported_at from import_log
    imp_res = await db.execute(select(func.max(ImportLog.imported_at)))
    last_imported_at = imp_res.scalar()

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
        "last_update": _to_wita(last_imported_at),
    }


# ─── SS Stats ───────────────────────────────────────────

@router.get("/ss/stats/{nrp}")
async def get_ss_stats(nrp: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
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
    user: dict = Depends(get_current_user),
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
    user: dict = Depends(get_current_user),
):
    query = select(SsRecord).where(SsRecord.nrp == nrp)
    if status:
        query = query.where(SsRecord.current_status.ilike(f"%{status}%"))

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    # Order by tanggal_menilai (approve date) DESC, fallback to updated_at
    from sqlalchemy import desc, nulls_last
    query = query.order_by(nulls_last(desc(SsRecord.tanggal_laporan)), desc(SsRecord.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    records = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [_ss_to_dict(r) for r in records],
    }


WITA = timezone(timedelta(hours=8))

def _to_wita(dt):
    """Convert UTC datetime to WITA ISO format: 2026-06-07T16:16:31+08:00"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    wita = dt.astimezone(WITA)
    # Force +HH:MM format (Python isoformat may return +HHMM for fixed offsets)
    base = wita.strftime("%Y-%m-%dT%H:%M:%S")
    ms = f".{wita.microsecond // 1000:03d}"
    off = wita.strftime("%z")
    off_fmt = f"{off[:3]}:{off[3:]}"
    return f"{base}{ms}{off_fmt}"

def _ss_to_dict(r: SsRecord) -> dict:
    return {
        "no_ss": r.no_ss,
        "judul": r.judul,
        "nrp": r.nrp,
        "nama": r.nama or None,
        "dept": r.dept,
        "tanggal_laporan": r.tanggal_laporan.isoformat() if r.tanggal_laporan else None,
        "current_status": r.current_status,
        "source": r.source,
        "grade_ss": r.grade_ss or None,
        "reward_ss": float(r.reward_ss) if r.reward_ss else None,
        "created_at": _to_wita(r.created_at),
    }


# ─── ESIC ───────────────────────────────────────────────

@router.get("/esic/by-nrp/{nrp}")
async def get_esic_by_nrp(nrp: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
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
    user: dict = Depends(get_current_user),
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
    user: dict = Depends(get_current_user),
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


# ─── Test ─────────────────────────────────────────────────


@router.get("/test-timezone")
async def test_timezone():
    """Test timezone — UTC vs WITA display."""
    now_utc = datetime.now(timezone.utc)
    now_wita = now_utc.astimezone(WITA)
    return {
        "utc": now_utc.isoformat(),
        "wita": now_wita.isoformat(),
        "note": "Timestamp di DB disimpan sebagai UTC, response API dikonversi ke WITA (+08:00)",
    }


