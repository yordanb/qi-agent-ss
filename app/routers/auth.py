"""Authentication endpoints with JWT."""

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
    user: dict  # {nrp, nama, role}

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
    # Strict check: User must exist in users table
    res = await db.execute(
        text("SELECT nrp, password_hash, role, is_active FROM tb_ss.users WHERE nrp = :nrp"),
        {"nrp": req.nrp},
    )
    user = res.mappings().first()

    if not user:
        raise HTTPException(status_code=401, detail="NRP tidak terdaftar")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Akun dinonaktifkan")

    # Verify password
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Password salah")

    # Get nama from manpower
    mp_res = await db.execute(
        text("SELECT nama FROM tb_ss.manpower WHERE nrp = :nrp LIMIT 1"),
        {"nrp": req.nrp},
    )
    mp_user = mp_res.mappings().first()
    nama = mp_user["nama"] if mp_user else req.nrp

    access_token = create_access_token({"sub": req.nrp, "role": user["role"]})
    refresh_token = create_refresh_token({"sub": req.nrp})
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={"nrp": req.nrp, "nama": nama, "role": user["role"]}
    )

@router.post("/refresh")
async def refresh_token(token: str, db: AsyncSession = Depends(get_db)):
    """Refresh expired access token."""
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    nrp = payload.get("sub")
    role = payload.get("role", "user")
    new_access = create_access_token({"sub": nrp, "role": role})
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
        text("SELECT password_hash, role FROM tb_ss.users WHERE nrp = :nrp"),
        {"nrp": req.admin_nrp},
    )
    admin = admin_res.mappings().first()
    if not admin or admin["role"] != "admin":
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
