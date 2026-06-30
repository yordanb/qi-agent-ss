from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User

async def get_user_by_nrp(db: AsyncSession, nrp: str) -> User | None:
    result = await db.execute(select(User).where(User.nrp == nrp))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, nrp: str, password_hash: str, role: str = 'user') -> User:
    user = User(nrp=nrp, password_hash=password_hash, role=role)
    db.add(user)
    await db.flush()
    return user
