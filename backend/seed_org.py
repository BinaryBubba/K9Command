"""
One-time seed script: creates the K9 Country Club organization record.
Run once after the organizations table is created.
Usage: python seed_org.py
"""
import asyncio
import os
from sqlalchemy import select
from database import async_session
from db_models import Organization

K9CC_ORG_ID = "00000000-0000-0000-0000-000000000001"

async def seed():
    async with async_session() as db:
        existing = (await db.execute(
            select(Organization).where(Organization.id == K9CC_ORG_ID)
        )).scalar_one_or_none()

        if existing:
            print(f"Organization already exists: {existing.name} ({existing.id})")
            return

        org = Organization(
            id=K9CC_ORG_ID,
            name="K9 Country Club",
            slug="k9cc",
            timezone="America/Chicago",
            contact_email=os.getenv("OWNER_EMAIL", ""),
            is_active=True,
            feature_flags={},
        )
        db.add(org)
        await db.commit()
        print(f"Created organization: {org.name} ({org.id})")

if __name__ == "__main__":
    asyncio.run(seed())
