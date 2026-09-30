from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User


async def get_user_by_nrp(db: AsyncSession, nrp: str) -> User | None:
    result = await db.execute(select(User).where(User.nrp == nrp))
    return result.scalar_one_or_none()


async def get_all_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.nrp))
    return result.scalars().all()


async def create_user(db: AsyncSession, nrp: str, password_hash: str, role: str = 'user') -> User:
    user = User(nrp=nrp, password_hash=password_hash, role=role)
    db.add(user)
    await db.flush()
    return user


async def update_user(db: AsyncSession, nrp: str, **kwargs) -> User | None:
    user = await get_user_by_nrp(db, nrp)
    if user:
        for key, value in kwargs.items():
            setattr(user, key, value)
        await db.flush()
    return user


async def delete_user(db: AsyncSession, nrp: str) -> bool:
    user = await get_user_by_nrp(db, nrp)
    if user:
        await db.delete(user)
        await db.flush()
        return True
    return False
