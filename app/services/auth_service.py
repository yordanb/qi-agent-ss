"""Auth service — business logic for authentication."""
import logging
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.repositories.user_repo import get_user_by_nrp, create_user

logger = logging.getLogger("qi-agent.auth")


async def login(db: AsyncSession, nrp: str, password: str) -> dict:
    """Login: verify credentials, return tokens + user info."""
    user = await get_user_by_nrp(db, nrp)

    if not user:
        # Auto-create user if NRP exists in manpower
        mp_res = await db.execute(
            text("SELECT nrp, nama FROM tb_ss.manpower WHERE nrp = :nrp LIMIT 1"),
            {"nrp": nrp},
        )
        mp_user = mp_res.mappings().first()
        if not mp_user:
            raise HTTPException(status_code=404, detail="NRP tidak ditemukan")

        default_hash = get_password_hash("12345")
        user = await create_user(db, nrp, default_hash)
        await db.commit()

        if not verify_password(password, default_hash):
            raise HTTPException(status_code=401, detail="Password salah. Default password: 12345")

        nama = mp_user["nama"] or nrp
    else:
        if not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Password salah")

        # Get nama from manpower
        mp_res = await db.execute(
            text("SELECT nama FROM tb_ss.manpower WHERE nrp = :nrp LIMIT 1"),
            {"nrp": nrp},
        )
        mp_user = mp_res.mappings().first()
        nama = mp_user["nama"] if mp_user else nrp

    access_token = create_access_token({"sub": nrp, "is_admin": user.is_admin})
    refresh_token = create_refresh_token({"sub": nrp})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "nrp": nrp,
        "nama": nama,
        "is_admin": user.is_admin,
    }


async def change_password(db: AsyncSession, nrp: str, old_password: str, new_password: str) -> dict:
    user = await get_user_by_nrp(db, nrp)
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    if not verify_password(old_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Password lama salah")

    user.password_hash = get_password_hash(new_password)
    await db.commit()
    return {"detail": "Password berhasil diubah"}
