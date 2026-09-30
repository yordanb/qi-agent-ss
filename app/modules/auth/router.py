"""Auth router — thin layer calling auth service."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_token, get_password_hash, get_current_user
from app.services.auth_service import login, change_password, create_new_user, list_users
from app.repositories import user_repo

logger = logging.getLogger("qi-agent.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ─────────────────────────────────────────────────

class LoginRequest(BaseModel):
    nrp: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class ChangePasswordRequest(BaseModel):
    nrp: str
    old_password: str
    new_password: str


class AdminResetPasswordRequest(BaseModel):
    nrp: str
    new_password: str


class CreateUserRequest(BaseModel):
    nrp: str
    password: str
    role: str = "user"


class UpdateUserRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


# ── Auth Endpoints ───────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def login_endpoint(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await login(db, req.nrp, req.password)


@router.post("/change-password")
async def change_password_endpoint(
    req: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await change_password(db, req.nrp, req.old_password, req.new_password)


@router.post("/logout")
async def logout_endpoint(current_user: dict = Depends(get_current_user)):
    logger.info("User %s logged out", current_user.get("sub"))
    return {"detail": "Logged out"}


@router.post("/admin/reset-password")
async def admin_reset_password(
    req: AdminResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Hanya admin")
    user = await user_repo.get_user_by_nrp(db, req.nrp)
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    user.password_hash = get_password_hash(req.new_password)
    await db.commit()
    return {"detail": "Password berhasil di-reset"}


# ── User Management Endpoints (Admin Only) ──────────────────

@router.get("/admin/users")
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all users (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Hanya admin")
    return await list_users(db)


@router.post("/admin/users")
async def create_user(
    req: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create new user (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Hanya admin")
    return await create_new_user(db, req.nrp, req.password, req.role)


@router.patch("/admin/users/{nrp}")
async def update_user(
    nrp: str,
    req: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update user role/status (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Hanya admin")
    if nrp == current_user.get("nrp"):
        raise HTTPException(status_code=400, detail="Tidak bisa update diri sendiri")
    user = await user_repo.update_user(db, nrp, role=req.role, is_active=req.is_active)
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    await db.commit()
    return {"nrp": user.nrp, "role": user.role, "is_active": user.is_active}


@router.delete("/admin/users/{nrp}")
async def delete_user(
    nrp: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete user (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Hanya admin")
    if nrp == current_user.get("nrp"):
        raise HTTPException(status_code=400, detail="Tidak bisa hapus diri sendiri")
    deleted = await user_repo.delete_user(db, nrp)
    if not deleted:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    await db.commit()
    return {"detail": f"User {nrp} berhasil dihapus"}
