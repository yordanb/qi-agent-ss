"""Auth router — thin layer calling auth service."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_token, get_password_hash, get_current_user
from app.services.auth_service import login, change_password
from app.repositories import user_repo

logger = logging.getLogger("qi-agent.auth")
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


class RefreshRequest(BaseModel):
    refresh_token: str


class AdminResetPasswordRequest(BaseModel):
    nrp: str
    new_password: str


@router.post("/login", response_model=LoginResponse)
async def login_endpoint(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await login(db, req.nrp, req.password)


@router.post("/refresh")
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(req.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    nrp = payload.get("sub")
    if not nrp:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = await user_repo.get_user_by_nrp(db, nrp)
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    return await login(db, nrp, "")  # TODO: proper token refresh


@router.post("/change-password")
async def change_password_endpoint(
    req: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await change_password(db, req.nrp, req.old_password, req.new_password)


@router.post("/logout")
async def logout_endpoint(current_user: dict = Depends(get_current_user)):
    """Logout — client-side only, but endpoint exists for consistency."""
    logger.info("User %s logged out", current_user.get("sub"))
    return {"detail": "Logged out"}


@router.post("/admin/reset-password")
async def admin_reset_password(
    req: AdminResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Hanya admin")
    user = await user_repo.get_user_by_nrp(db, req.nrp)
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    user.password_hash = get_password_hash(req.new_password)
    await db.commit()
    return {"detail": "Password berhasil di-reset"}
