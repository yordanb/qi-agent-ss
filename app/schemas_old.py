from datetime import date, datetime
from pydantic import BaseModel, Field
from typing import Optional

class SsRecordOut(BaseModel):
    no_ss: str
    judul: str
    nrp: str
    nama: str
    dept: str
    divisi: str
    distrik: str
    tanggal_laporan: Optional[date]
    grade_ss: str
    kualitas_ss: str
    kategori_ss: str
    reward_ss: float
    status_karyawan: str
    manfaat_financial: Optional[float]
    tanggal_menilai: Optional[date]
    dinilai_oleh: str
    current_status: str
    source: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SsStatsOut(BaseModel):
    nrp: str
    nama: str
    dept: str
    total_ss: int
    closed: int
    outstanding: int
    wait_approval: int
    other: int
    last_update: Optional[str] = None

class DeptStatsOut(BaseModel):
    dept: str
    total_ss: int
    closed: int
    outstanding: int
    grade_f: int
    grade_e: int
    grade_d: int
    grade_c: int

class ImportResult(BaseModel):
    filename: str
    source_type: str
    total_rows: int
    new_records: int
    updated_records: int
    import_id: int

class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    data: list[SsRecordOut]
