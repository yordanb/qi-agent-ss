from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class EsicSnapshotResponse(BaseModel):
    id: Optional[int] = None
    nrp: str
    nama: Optional[str] = None
    dept: Optional[str] = None
    divisi: Optional[str] = None
    distrik: Optional[str] = None
    posisi: Optional[str] = None
    snapshot_date: Optional[str] = None
    dokumen_diakses: Optional[str] = None
    dokumen_mtd: Optional[str] = None
    monthly_metrics: Optional[Any] = None
    created_at: Optional[str] = None

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.id,
            nrp=obj.nrp,
            nama=obj.user.nama if obj.user else None,
            dept=obj.user.dept if obj.user else None,
            snapshot_date=obj.snapshot_date.isoformat() if obj.snapshot_date else None,
            dokumen_diakses=obj.dokumen_diakses,
            dokumen_mtd=obj.dokumen_mtd,
        )


class EsicListResponse(BaseModel):
    data: List[EsicSnapshotResponse]
