"""SS service — business logic for SS endpoints."""
import logging
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.ss_repo import (
    get_ss_stats, get_ss_list, get_dept_stats, get_dept_daily, get_last_import_time, get_eiictm_stats,
)
from app.models import SsRecord

logger = logging.getLogger("qi-agent.ss")

WITA = timezone.utc  # Placeholder — actual WITA conversion in router


async def _get_user_nama(db: AsyncSession, nrp: str) -> str:
    result = await db.execute(
        text("SELECT nama FROM tb_ss.manpower WHERE nrp = :nrp LIMIT 1"),
        {"nrp": nrp},
    )
    row = result.scalar()
    return row or nrp


async def _get_user_dept(db: AsyncSession, nrp: str) -> str:
    result = await db.execute(
        text("SELECT dept FROM tb_ss.ss_records WHERE nrp = :nrp LIMIT 1"),
        {"nrp": nrp},
    )
    return result.scalar() or "-"


async def get_stats_response(db: AsyncSession, nrp: str) -> dict:
    stats = await get_ss_stats(db, nrp)
    nama = await _get_user_nama(db, nrp)
    dept = await _get_user_dept(db, nrp)
    last_import = await get_last_import_time(db)
    return {"nrp": nrp, "nama": nama, "dept": dept, **stats, "last_update": last_import}

async def get_monthly_response(db: AsyncSession, nrp: str, year: int, month: int) -> dict:
    stats = await get_ss_stats(db, nrp, year=year, month=month)
    nama = await _get_user_nama(db, nrp)
    dept = await _get_user_dept(db, nrp)
    return {"nrp": nrp, "nama": nama, "dept": dept, "year": year, "month": month, **stats}


async def get_monthly_response(db: AsyncSession, nrp: str, year: int, month: int) -> dict:
    stats = await get_ss_stats(db, nrp, year=year, month=month)
    nama = await _get_user_nama(db, nrp)
    dept = await _get_user_dept(db, nrp)
    return {"nrp": nrp, "nama": nama, "dept": dept, "year": year, "month": month, **stats}


async def get_list_response(db: AsyncSession, nrp: str, page: int, page_size: int, status: str = None) -> dict:
    result = await get_ss_list(db, nrp, page=page, page_size=page_size, status=status)
    records = result.pop("data")
    return {**result, "data": [_ss_to_dict(r) for r in records]}


async def get_dept_stats_response(db: AsyncSession, dept: str, year: int = None, month: int = None) -> dict:
    return await get_dept_stats(db, dept, year=year, month=month)


async def get_dept_daily_response(db: AsyncSession, dept: str, year: int, month: int) -> dict:
    return await get_dept_daily(db, dept, year=year, month=month)

async def get_eiictm_response(db: AsyncSession, dept: str, year: int = None, month: int = None) -> dict:
    return await get_eiictm_stats(db, dept, year=year, month=month)


def _ss_to_dict(r: SsRecord) -> dict:
    return {
        "no_ss": r.no_ss,
        "judul": r.judul,
        "nrp": r.nrp,
        "nama": r.nama,
        "dept": r.dept,
        "tanggal_laporan": r.tanggal_laporan.isoformat() if r.tanggal_laporan else None,
        "current_status": r.current_status,
        "grade_ss": r.grade_ss,
        "created_at": r.created_at,
    }
