from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.repositories.user_repo import get_user_by_nrp

async def login(db: AsyncSession, nrp: str, password: str) -> dict:
    user = await get_user_by_nrp(db, nrp)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User tidak aktif atau tidak terdaftar")
    
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Password salah")
    
    mp_res = await db.execute(text("SELECT nama FROM tb_ss.manpower WHERE nrp = :nrp LIMIT 1"), {"nrp": nrp})
    nama = mp_res.scalar() or nrp
    
    return {
        "access_token": create_access_token({"sub": nrp, "role": user.role}),
        "refresh_token": create_refresh_token({"sub": nrp}),
        "token_type": "bearer",
        "user": {"nrp": nrp, "nama": nama, "role": user.role}
    }

async def change_password(db, nrp, old, new):
    user = await get_user_by_nrp(db, nrp)
    if not user or not verify_password(old, user.password_hash):
        raise HTTPException(status_code=401, detail="Auth gagal")
    user.password_hash = get_password_hash(new)
    await db.commit()
    return {"detail": "OK"}
