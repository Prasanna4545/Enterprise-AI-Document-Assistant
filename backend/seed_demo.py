import asyncio
import uuid
from app.db.session import AsyncSessionLocal, engine
from app.models.models import Base, User, UserRole, Organization
from app.core.security import hash_password
from sqlalchemy import select


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as s:
        res = await s.execute(select(Organization).where(Organization.name == "Acme Corporation"))
        org = res.scalar_one_or_none()
        if not org:
            org = Organization(id=str(uuid.uuid4()), name="Acme Corporation")
            s.add(org)
            await s.commit()

        u_res = await s.execute(select(User).where(User.email == "admin@enterprise.com"))
        u = u_res.scalar_one_or_none()
        if not u:
            u = User(
                id=str(uuid.uuid4()),
                org_id=org.id,
                email="admin@enterprise.com",
                hashed_password=hash_password("AdminPass123!"),
                full_name="Demo Admin User",
                role=UserRole.ADMIN
            )
            s.add(u)
            await s.commit()
            print("[SUCCESS] Demo Admin User created: admin@enterprise.com / AdminPass123!")
        else:
            print("[SUCCESS] Demo Admin User already exists: admin@enterprise.com / AdminPass123!")

if __name__ == "__main__":
    asyncio.run(seed())
