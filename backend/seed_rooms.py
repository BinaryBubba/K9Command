"""
Seed script: creates K9CC's 8 rooms and 2 service types.
Run once after rooms and service_types tables are created.
Usage: python seed_rooms.py
"""
import asyncio
import uuid
from sqlalchemy import select
from database import async_session
from db_models import Room, ServiceType

ORG_ID = "00000000-0000-0000-0000-000000000001"

ROOMS = [
    {"name": "Room 1", "max_dogs": 3, "adjacency_group": "A", "sort_order": 1},
    {"name": "Room 2", "max_dogs": 3, "adjacency_group": "A", "sort_order": 2},
    {"name": "Room 3", "max_dogs": 3, "adjacency_group": "A", "sort_order": 3},
    {"name": "Room 4", "max_dogs": 3, "adjacency_group": "A", "sort_order": 4},
    {"name": "Room 5", "max_dogs": 3, "adjacency_group": "B", "sort_order": 5},
    {"name": "Room 6", "max_dogs": 3, "adjacency_group": "B", "sort_order": 6},
    {"name": "Room 7", "max_dogs": 3, "adjacency_group": "B", "sort_order": 7},
    {"name": "Room 8", "max_dogs": 3, "adjacency_group": "B", "sort_order": 8},
]

SERVICE_TYPES = [
    {"name": "Boarding", "code": "boarding", "is_overnight": True, "display_color": "#3B82F6"},
    {"name": "Daycare", "code": "daycare", "is_overnight": False, "display_color": "#10B981"},
]

async def seed():
    async with async_session() as db:
        # Seed rooms
        existing_rooms = (await db.execute(
            select(Room).where(Room.organization_id == ORG_ID)
        )).scalars().all()

        if existing_rooms:
            print(f"Rooms already seeded ({len(existing_rooms)} found)")
        else:
            for r in ROOMS:
                room = Room(
                    id=str(uuid.uuid4()),
                    organization_id=ORG_ID,
                    name=r["name"],
                    max_dogs=r["max_dogs"],
                    adjacency_group=r["adjacency_group"],
                    sort_order=r["sort_order"],
                    is_active=True,
                    is_out_of_service=False,
                )
                db.add(room)
            print(f"Created {len(ROOMS)} rooms")

        # Seed service types
        existing_services = (await db.execute(
            select(ServiceType).where(ServiceType.organization_id == ORG_ID)
        )).scalars().all()

        if existing_services:
            print(f"Service types already seeded ({len(existing_services)} found)")
        else:
            for s in SERVICE_TYPES:
                st = ServiceType(
                    id=str(uuid.uuid4()),
                    organization_id=ORG_ID,
                    name=s["name"],
                    code=s["code"],
                    is_overnight=s["is_overnight"],
                    display_color=s["display_color"],
                    is_active=True,
                )
                db.add(st)
            print(f"Created {len(SERVICE_TYPES)} service types")

        await db.commit()
        print("Done")

if __name__ == "__main__":
    asyncio.run(seed())
