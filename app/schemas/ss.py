from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class SsResponse(BaseModel):
    no_ss: str
    judul: str
    nrp: str
    nama: Optional[str] = None
    dept: Optional[str] = None
    tanggal_laporan: Optional[str] = None
    current_status: Optional[str] = None
    source: Optional[str] = None
    reward_ss: Optional[float] = None
    created_at: Optional[str] = None


class SsListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    data: List[Any]


class SsStatsResponse(BaseModel):
    nrp: str
    nama: str
    dept: str
    total_ss: int
    closed: int
    outstanding: int
    wait_approval: int
    other: int
    last_update: str


class MonthlyStatsResponse(BaseModel):
    nrp: str
    nama: str
    dept: str
    year: int
    month: int
    total_ss: int
    closed: int
    wait_approval: int
    other: int
