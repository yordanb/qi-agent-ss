"""Manpower + Coverage dashboard endpoints."""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func, and_, extract
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user

router = APIRouter()

# ─── Coverage by Section ─────────────────────────────────

@router.get("/manpower/coverage/section")
async def get_coverage_by_section(
    section: Optional[str] = None,
    year: int = Query(default=datetime.now().year),
    month: int = Query(default=datetime.now().month),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Coverage report per crew dalam satu section."""
    where_section = "AND m.section = :section" if section else ""
    params = {"year": year, "month": month}
    if section:
        params["section"] = section

    result = await db.execute(
        text(f"""
            SELECT
                m.crew,
                m.section,
                COUNT(DISTINCT m.nrp) AS total_people,
                COUNT(s.no_ss) AS total_ss,
                COALESCE(MAX(m.target_ss), 0) AS target_ss,
                ROUND(COUNT(s.no_ss)::numeric / NULLIF(COUNT(DISTINCT m.nrp) * COALESCE(MAX(m.target_ss), 1), 0) * 100, 1) AS coverage_pct
            FROM tb_ss.manpower m
            LEFT JOIN tb_ss.ss_records s
                ON s.nrp = m.nrp
                AND EXTRACT(YEAR FROM s.tanggal_laporan) = :year
                AND EXTRACT(MONTH FROM s.tanggal_laporan) = :month
            WHERE 1=1 {where_section}
            GROUP BY m.crew, m.section
            ORDER BY m.section, m.crew
        """),
        params,
    )
    rows = result.mappings().all()
    return {
        "year": year,
        "month": month,
        "section_filter": section,
        "data": [
            {
                "crew": r["crew"],
                "section": r["section"],
                "total_people": r["total_people"],
                "total_ss": r["total_ss"],
                "target_ss": r["target_ss"],
                "coverage_pct": float(r["coverage_pct"]) if r["coverage_pct"] else 0.0,
            }
            for r in rows
        ],
    }


# ─── Coverage by NRP (Individual) ───────────────────────

@router.get("/manpower/coverage/nrp/{nrp}")
async def get_coverage_by_nrp(
    nrp: str,
    year: int = Query(default=datetime.now().year),
    month: int = Query(default=datetime.now().month),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Coverage report individual — SS vs target."""
    result = await db.execute(
        text("""
            SELECT
                m.nrp, m.nama, m.section, m.crew, m.posisi,
                m.target_ss, m.status, m.jabatan,
                COUNT(s.no_ss) AS ss_count
            FROM tb_ss.manpower m
            LEFT JOIN tb_ss.ss_records s
                ON s.nrp = m.nrp
                AND EXTRACT(YEAR FROM s.tanggal_laporan) = :year
                AND EXTRACT(MONTH FROM s.tanggal_laporan) = :month
            WHERE m.nrp = :nrp
            GROUP BY m.nrp, m.nama, m.section, m.crew, m.posisi,
                     m.target_ss, m.status, m.jabatan
        """),
        {"nrp": nrp, "year": year, "month": month},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="NRP tidak ditemukan di manpower")

    target = row["target_ss"] or 0
    ss_count = row["ss_count"]
    coverage = round(ss_count / target * 100, 1) if target > 0 else 0.0

    return {
        "nrp": row["nrp"],
        "nama": row["nama"],
        "section": row["section"],
        "crew": row["crew"],
        "posisi": row["posisi"],
        "jabatan": row["jabatan"],
        "status": row["status"],
        "target_ss": target,
        "ss_count": ss_count,
        "coverage_pct": coverage,
        "year": year,
        "month": month,
    }


# ─── Coverage Summary (per section) ─────────────────────

@router.get("/manpower/coverage/summary")
async def get_coverage_summary(
    year: int = Query(default=datetime.now().year),
    month: int = Query(default=datetime.now().month),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Ringkasan coverage per crew — untuk dashboard."""
    result = await db.execute(
        text("""
            SELECT
                m.crew,
                COUNT(DISTINCT m.nrp) AS total_people,
                COUNT(s.no_ss) AS total_ss,
                SUM(COALESCE(m.target_ss, 0)) AS total_target,
                ROUND(COUNT(s.no_ss)::numeric / NULLIF(SUM(COALESCE(m.target_ss, 0)), 0) * 100, 1) AS coverage_pct
            FROM tb_ss.manpower m
            LEFT JOIN tb_ss.ss_records s
                ON s.nrp = m.nrp
                AND EXTRACT(YEAR FROM s.tanggal_laporan) = :year
                AND EXTRACT(MONTH FROM s.tanggal_laporan) = :month
            GROUP BY m.crew
            ORDER BY coverage_pct DESC
        """),
        {"year": year, "month": month},
    )
    rows = result.mappings().all()
    return {
        "year": year,
        "month": month,
        "data": [
            {
                "crew": r["crew"],
                "total_people": r["total_people"],
                "total_ss": r["total_ss"],
                "total_target": r["total_target"],
                "coverage_pct": float(r["coverage_pct"]) if r["coverage_pct"] else 0.0,
            }
            for r in rows
        ],
    }


# ─── Manpower List (CRUD read) ──────────────────────────

@router.get("/manpower")
async def get_manpower_list(
    section: Optional[str] = None,
    crew: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List manpower records — filterable by section/crew."""
    conditions = []
    params = {}
    if section:
        conditions.append("m.section = :section")
        params["section"] = section
    if crew:
        conditions.append("m.crew = :crew")
        params["crew"] = crew

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Count
    count_res = await db.execute(
        text(f"SELECT COUNT(*) FROM tb_ss.manpower m {where}"),
        params,
    )
    total = count_res.scalar()

    # Data
    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size
    result = await db.execute(
        text(f"""
            SELECT m.* FROM tb_ss.manpower m {where}
            ORDER BY m.section, m.crew, m.nama
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    rows = result.mappings().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [
            {
                "id": r["id"],
                "nrp": r["nrp"],
                "nama": r["nama"],
                "section": r["section"],
                "crew": r["crew"],
                "posisi": r["posisi"],
                "target_ss": r["target_ss"],
                "status": r["status"],
                "jabatan": r["jabatan"],
            }
            for r in rows
        ],
    }


# ─── Manpower CRUD ──────────────────────────────────────

@router.post("/manpower")
async def create_manpower(data: dict, db: AsyncSession = Depends(get_db)):
    """Bulk insert manpower records."""
    records = data.get("records", [])
    if not records:
        raise HTTPException(status_code=400, detail="No records provided")

    inserted = 0
    for rec in records:
        try:
            await db.execute(
                text("""
                    INSERT INTO tb_ss.manpower (nrp, nama, section, crew, posisi, target_ss, status, jabatan)
                    VALUES (:nrp, :nama, :section, :crew, :posisi, :target_ss, :status, :jabatan)
                """),
                {
                    "nrp": rec.get("nrp"),
                    "nama": rec.get("nama"),
                    "section": rec.get("section"),
                    "crew": rec.get("crew"),
                    "posisi": rec.get("posisi"),
                    "target_ss": rec.get("target_ss", 0),
                    "status": rec.get("status"),
                    "jabatan": rec.get("jabatan"),
                },
            )
            inserted += 1
        except Exception:
            continue

    await db.commit()
    return {"inserted": inserted, "total": len(records)}


@router.delete("/manpower")
async def clear_manpower(db: AsyncSession = Depends(get_db)):
    """Clear all manpower data (for re-import)."""
    await db.execute(text("DELETE FROM tb_ss.manpower"))
    await db.commit()
    return {"message": "All manpower records deleted"}

@router.delete("/manpower/{id}")
async def delete_manpower(id: int, db: AsyncSession = Depends(get_db)):
    """Hapus satu record manpower berdasarkan ID."""
    result = await db.execute(text("DELETE FROM tb_ss.manpower WHERE id = :id"), {"id": id})
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="ID tidak ditemukan")
    await db.commit()
    return {"message": f"Record {id} deleted"}


@router.put("/manpower/{id}")
async def update_manpower(id: int, data: dict, db: AsyncSession = Depends(get_db)):
    """Update satu record manpower berdasarkan ID."""
    fields = []
    params = {"id": id}
    for key in ("nrp", "nama", "section", "crew", "posisi", "target_ss", "status", "jabatan"):
        if key in data:
            fields.append(f"{key} = :{key}")
            params[key] = data[key]

    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await db.execute(
        text(f"UPDATE tb_ss.manpower SET {', '.join(fields)} WHERE id = :id"),
        params,
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="ID tidak ditemukan")
    await db.commit()

    # Return updated record
    res = await db.execute(text("SELECT * FROM tb_ss.manpower WHERE id = :id"), {"id": id})
    row = res.mappings().first()
    return {
        "id": row["id"],
        "nrp": row["nrp"],
        "nama": row["nama"],
        "section": row["section"],
        "crew": row["crew"],
        "posisi": row["posisi"],
        "target_ss": row["target_ss"],
        "status": row["status"],
        "jabatan": row["jabatan"],
    }


@router.post("/manpower/single")
async def create_single_manpower(data: dict, db: AsyncSession = Depends(get_db)):
    """Tambah satu record manpower."""
    nrp = data.get("nrp")
    if not nrp:
        raise HTTPException(status_code=400, detail="NRP wajib diisi")

    result = await db.execute(
        text("""
            INSERT INTO tb_ss.manpower (nrp, nama, section, crew, posisi, target_ss, status, jabatan)
            VALUES (:nrp, :nama, :section, :crew, :posisi, :target_ss, :status, :jabatan)
            RETURNING id
        """),
        {
            "nrp": nrp,
            "nama": data.get("nama", ""),
            "section": data.get("section", ""),
            "crew": data.get("crew", ""),
            "posisi": data.get("posisi", ""),
            "target_ss": data.get("target_ss", 2),
            "status": data.get("status", "Aktif"),
            "jabatan": data.get("jabatan", ""),
        },
    )
    new_id = result.scalar()
    await db.commit()

    res = await db.execute(text("SELECT * FROM tb_ss.manpower WHERE id = :id"), {"id": new_id})
    row = res.mappings().first()
    return {
        "id": row["id"],
        "nrp": row["nrp"],
        "nama": row["nama"],
        "section": row["section"],
        "crew": row["crew"],
        "posisi": row["posisi"],
        "target_ss": row["target_ss"],
        "status": row["status"],
        "jabatan": row["jabatan"],
    }
