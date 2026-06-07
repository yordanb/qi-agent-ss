"""User repository — DB operations for users table."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User


async def get_user_by_nrp(db: AsyncSession, nrp: str) -> User | None:
    result = await db.execute(select(User).where(User.nrp == nrp))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, nrp: str, password_hash: str, is_admin: bool = False) -> User:
    user = User(nrp=nrp, password_hash=password_hash, is_admin=is_admin)
    db.add(user)
    await db.flush()
    return user


async def update_password(db: AsyncSession, user: User, new_hash: str) -> None:
    user.password_hash = new_hash
    await db.flush()
