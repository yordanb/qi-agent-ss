"""Authentication endpoints with JWT."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    nrp: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    nrp: str
    nama: str
    is_admin: bool = False

class ChangePasswordRequest(BaseModel):
    nrp: str
    old_password: str
    new_password: str

class AdminResetRequest(BaseModel):
    admin_nrp: str
    admin_password: str
    target_nrp: str
    new_password: str

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with NRP + password → returns JWT tokens."""
    res = await db.execute(
        text("SELECT nrp, password_hash, is_admin FROM tb_ss.users WHERE nrp = :nrp"),
        {"nrp": req.nrp},
    )
    user = res.mappings().first()

    if not user:
        # Auto-create user if NRP exists in SS data
        ss_res = await db.execute(
            text("SELECT nrp, nama FROM tb_ss.ss_records WHERE nrp = :nrp LIMIT 1"),
            {"nrp": req.nrp},
        )
        ss_user = ss_res.mappings().first()
        if not ss_user:
            raise HTTPException(status_code=404, detail="NRP tidak ditemukan")

        default_hash = get_password_hash("12345")
        await db.execute(
            text("INSERT INTO tb_ss.users (nrp, password_hash) VALUES (:nrp, :hash)"),
            {"nrp": req.nrp, "hash": default_hash},
        )
        await db.commit()

        if not verify_password(req.password, default_hash):
            raise HTTPException(status_code=401, detail="Password salah. Default password: 12345")

        nama = ss_user["nama"] or req.nrp
        access_token = create_access_token({"sub": req.nrp, "is_admin": False})
        refresh_token = create_refresh_token({"sub": req.nrp})
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            nrp=req.nrp,
            nama=nama,
            is_admin=False,
        )

    # Verify password for existing user
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Password salah")

    # Get nama from SS data
    ss_res = await db.execute(
        text("SELECT nama FROM tb_ss.ss_records WHERE nrp = :nrp LIMIT 1"),
        {"nrp": req.nrp},
    )
    ss_user = ss_res.mappings().first()
    nama = ss_user["nama"] if ss_user else req.nrp
    is_admin = user["is_admin"] or False

    access_token = create_access_token({"sub": req.nrp, "is_admin": is_admin})
    refresh_token = create_refresh_token({"sub": req.nrp})
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        nrp=req.nrp,
        nama=nama,
        is_admin=is_admin,
    )

@router.post("/refresh")
async def refresh_token(token: str, db: AsyncSession = Depends(get_db)):
    """Refresh expired access token."""
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    nrp = payload.get("sub")
    is_admin = payload.get("is_admin", False)
    new_access = create_access_token({"sub": nrp, "is_admin": is_admin})
    new_refresh = create_refresh_token({"sub": nrp})
    return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}

@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, db: AsyncSession = Depends(get_db)):
    """Ganti password sendiri."""
    res = await db.execute(
        text("SELECT password_hash FROM tb_ss.users WHERE nrp = :nrp"),
        {"nrp": req.nrp},
    )
    user = res.mappings().first()
    if not user:
        raise HTTPException(status_code=404, detail="NRP tidak ditemukan")

    if not verify_password(req.old_password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Password lama salah")

    new_hash = get_password_hash(req.new_password)
    await db.execute(
        text("UPDATE tb_ss.users SET password_hash = :hash WHERE nrp = :nrp"),
        {"hash": new_hash, "nrp": req.nrp},
    )
    await db.commit()
    return {"message": "Password berhasil diubah"}

@router.post("/admin/reset-password")
async def admin_reset_password(req: AdminResetRequest, db: AsyncSession = Depends(get_db)):
    """Admin reset password user lain."""
    admin_res = await db.execute(
        text("SELECT password_hash, is_admin FROM tb_ss.users WHERE nrp = :nrp"),
        {"nrp": req.admin_nrp},
    )
    admin = admin_res.mappings().first()
    if not admin or not admin["is_admin"]:
        raise HTTPException(status_code=403, detail="Hanya admin yang bisa reset password")

    if not verify_password(req.admin_password, admin["password_hash"]):
        raise HTTPException(status_code=401, detail="Password admin salah")

    target_res = await db.execute(
        text("SELECT nrp FROM tb_ss.users WHERE nrp = :nrp"),
        {"nrp": req.target_nrp},
    )
    if not target_res.mappings().first():
        raise HTTPException(status_code=404, detail=f"NRP {req.target_nrp} tidak ditemukan")

    new_hash = get_password_hash(req.new_password)
    await db.execute(
        text("UPDATE tb_ss.users SET password_hash = :hash WHERE nrp = :nrp"),
        {"hash": new_hash, "nrp": req.target_nrp},
    )
    await db.commit()
    return {"message": f"Password NRP {req.target_nrp} berhasil direset"}
