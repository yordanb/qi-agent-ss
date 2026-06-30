"""SS router — thin layer calling SS service."""
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.ss_service import (
    get_stats_response, get_monthly_response, get_list_response,
    get_dept_stats_response, get_dept_daily_response, get_eiictm_response,
)

logger = logging.getLogger("qi-agent.ss")
router = APIRouter(prefix="/ss", tags=["ss"])

WITA = timezone(timedelta(hours=8))


def _to_wita(dt):
    """Convert UTC datetime to WITA ISO format: 2026-06-07T16:16:31+08:00"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    wita = dt.astimezone(WITA)
    offset = wita.strftime("%z")
    offset_fmt = f"{offset[:3]}:{offset[3:]}"
    base = wita.strftime("%Y-%m-%dT%H:%M:%S")
    ms = f".{wita.microsecond // 1000:03d}"
    return f"{base}{ms}{offset_fmt}"


@router.get("/stats/{nrp}")
async def get_ss_stats(nrp: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    try:
        response = await get_stats_response(db, nrp)
        response["last_update"] = _to_wita(response["last_update"])
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_ss_stats error for nrp=%s: %s", nrp, str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats/{nrp}/monthly")
async def get_monthly_stats(
    nrp: str,
    year: int = Query(default=2026, ge=2020, le=2030),
    month: int = Query(default=6, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    try:
        return await get_monthly_response(db, nrp, year, month)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_monthly_stats error for nrp=%s: %s", nrp, str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/by-nrp/{nrp}")
async def get_ss_by_nrp(
    nrp: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    try:
        return await get_list_response(db, nrp, page, page_size, status)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_ss_by_nrp error for nrp=%s: %s", nrp, str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/dept/stats/{dept}")
async def get_dept_stats(
    dept: str,
    year: int = Query(default=None, ge=2020, le=2030),
    month: int = Query(default=None, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    try:
        return await get_dept_stats_response(db, dept, year, month)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_dept_stats error: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/dept/eiictm/{dept}")
async def get_eiictm_stats(
    dept: str,
    year: int = Query(default=None, ge=2020, le=2030),
    month: int = Query(default=None, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    try:
        return await get_eiictm_response(db, dept, year=year, month=month)
    except Exception as e:
        logger.error("get_eiictm_stats error: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/dept/daily/{dept}")
async def get_dept_daily(
    dept: str,
    year: int = Query(default=None, ge=2020, le=2030),
    month: int = Query(default=None, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    try:
        return await get_dept_daily_response(db, dept, year, month)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_dept_daily error: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/test-timezone")
async def test_timezone():
    now = datetime.now(timezone.utc)
    return {
        "utc": now.isoformat(),
        "wita": _to_wita(now),
    }
