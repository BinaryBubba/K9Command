from uuid import uuid4
import os
from datetime import datetime, date, timezone
from typing import Optional, List
import uuid

from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_db, init_db
from db_models import User as UserORM, Dog as DogORM, Location as LocationORM, Booking as BookingORM, Task as TaskORM, Shift as ShiftORM, AuditLog as AuditLogORM, TimeEntry as TimeEntryORM, TimeModificationRequest as TimeModificationRequestORM, UserRole, BookingStatus, AccommodationType, TaskStatus, StaffRequest, StaffRequestStatus, AuditAction, TimeModificationStatus, FormTemplateORM, FormSubmissionORM
from models import UserCreate, LoginRequest, LoginResponse, UserResponse
from auth import hash_password, verify_password, create_access_token, require_role
from app.routes.daily_updates import router as daily_updates_router


# TEMP: in-memory form store (to be replaced with DB)
FORM_TEMPLATES = {}

app = FastAPI(title="K9Command API")
app.include_router(daily_updates_router, prefix="/api")





from sqlalchemy import text

@app.get("/api/health")
async def health(db: AsyncSession = Depends(get_db)):
    """
    Docker/Caddy healthcheck endpoint.
    Confirms API is running AND Postgres is reachable.
    """
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail={"status": "degraded", "db": "down", "error": str(e)})

# CORS
public_origins = os.getenv("PUBLIC_ORIGINS")
allow_origins = [o.strip() for o in public_origins.split(",")] if public_origins else [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DEV MODE (bypass for owner-only ops during build-out) ---
DEV_MODE = os.getenv("DEV_MODE", "false").lower() in ("1", "true", "yes", "on")
AUTO_INIT_DB = os.getenv("AUTO_INIT_DB", "false").lower() in ("1", "true", "yes", "on")
DEV_ADMIN_SECRET = os.getenv("DEV_ADMIN_SECRET", "")

def dev_auth_ok(x_dev_secret: Optional[str]) -> bool:
    return DEV_MODE and DEV_ADMIN_SECRET and x_dev_secret == DEV_ADMIN_SECRET

async def require_owner_or_dev(
    x_dev_secret: Optional[str],
    current_user: UserORM,
):
    if current_user.is_owner:
        return
    if dev_auth_ok(x_dev_secret):
        return
    raise HTTPException(status_code=403, detail="Owner privileges required")

# --- Startup: ensure tables + seed owner if env provided ---
@app.on_event("startup")
async def on_startup():
    if AUTO_INIT_DB:
        await init_db()
    await seed_owner_if_needed()

async def seed_owner_if_needed():
    """
    If OWNER_EMAIL/OWNER_PASSWORD are set and no owner exists, create it.
    """
    if not hasattr(UserORM, "is_owner"):
        print("⚠️ UserORM.is_owner missing; skipping owner seed on startup")
        return

    owner_email = os.getenv("OWNER_EMAIL")
    owner_password = os.getenv("OWNER_PASSWORD")
    owner_name = os.getenv("OWNER_FULL_NAME", "Owner")
    owner_phone = os.getenv("OWNER_PHONE")

    if not owner_email or not owner_password:
        return

    # Use a direct session
    async for db in get_db():
        # If any owner exists, do nothing
        existing_owner = (await db.execute(
            select(UserORM).where(UserORM.is_owner == True)
        )).scalar_one_or_none()
        if existing_owner:
            return

        # If email already exists, promote to owner/admin
        existing_user = (await db.execute(
            select(UserORM).where(UserORM.email == owner_email)
        )).scalar_one_or_none()

        if existing_user:
            existing_user.role = UserRole.ADMIN
            existing_user.is_owner = True
            existing_user.is_active = True
            await db.commit()
            print(f"✅ Promoted existing user to OWNER: {owner_email}")
            return

        # Create new owner
        user = UserORM(
            email=owner_email,
            hashed_password=hash_password(owner_password),
            full_name=owner_name,
            phone=owner_phone,
            role=UserRole.ADMIN,
            is_owner=True,
            is_active=True,
            household_id=None,
        )
        db.add(user)
        await db.commit()
        print(f"✅ Seeded OWNER account: {owner_email}")
        return


# ---------------- AUTH ----------------

@app.post("/api/auth/register", response_model=LoginResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    PUBLIC REGISTRATION: CUSTOMER ONLY (role input ignored)
    """
    existing = (await db.execute(select(UserORM).where(UserORM.email == user_data.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Force customer role
    household_id = os.urandom(16).hex()
    user = UserORM(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        role=UserRole.CUSTOMER,
        household_id=household_id,
        is_active=True,
        is_owner=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value, "is_owner": user.is_owner})
    return LoginResponse(
        token=token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            role=user.role.value,
            is_active=user.is_active,
            household_id=user.household_id,
            created_at=user.created_at,
        ),
    )


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(UserORM).where(UserORM.email == login_data.email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is disabled")

    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value, "is_owner": user.is_owner})
    return LoginResponse(
        token=token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            role=user.role.value,
            is_active=user.is_active,
            household_id=user.household_id,
            created_at=user.created_at,
        ),
    )


@app.post("/api/auth/request-staff")
async def request_staff_access(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Staff workflow:
    - creates a staff request (pending)
    - does NOT create a user until approved
    """
    # prevent if user exists
    existing_user = (await db.execute(select(UserORM).where(UserORM.email == user_data.email))).scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered as a user")

    existing_req = (await db.execute(select(StaffRequest).where(StaffRequest.email == user_data.email))).scalar_one_or_none()
    if existing_req and existing_req.status == StaffRequestStatus.PENDING:
        raise HTTPException(status_code=409, detail="A pending staff request already exists for this email")

    # Upsert: if request exists but rejected, allow re-request by overwriting
    if existing_req:
        existing_req.full_name = user_data.full_name
        existing_req.phone = user_data.phone
        existing_req.hashed_password = hash_password(user_data.password)
        existing_req.status = StaffRequestStatus.PENDING
        existing_req.reviewed_by = None
        existing_req.reviewed_at = None
        existing_req.review_notes = None
        await db.commit()
        return {"status": "pending", "message": "Staff request re-submitted"}

    req = StaffRequest(
        email=user_data.email,
        full_name=user_data.full_name,
        phone=user_data.phone,
        hashed_password=hash_password(user_data.password),
        status=StaffRequestStatus.PENDING,
    )
    db.add(req)
    await db.commit()
    return {"status": "pending", "message": "Staff request submitted"}


# ---------------- ADMIN ----------------

@app.get("/api/admin/staff-requests")
async def list_staff_requests(
    db: AsyncSession = Depends(get_db),
    admin_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    res = await db.execute(select(StaffRequest).order_by(StaffRequest.created_at.desc()))
    items = res.scalars().all()
    return [
        {
            "id": r.id,
            "email": r.email,
            "full_name": r.full_name,
            "phone": r.phone,
            "status": r.status.value,
            "created_at": r.created_at,
            "reviewed_by": r.reviewed_by,
            "reviewed_at": r.reviewed_at,
            "review_notes": r.review_notes,
        }
        for r in items
    ]


@app.post("/api/admin/staff-requests/{request_id}/approve")
async def approve_staff_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    req = (await db.execute(select(StaffRequest).where(StaffRequest.id == request_id))).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != StaffRequestStatus.PENDING:
        raise HTTPException(status_code=409, detail=f"Request is not pending (status={req.status.value})")

    # create staff user
    existing_user = (await db.execute(select(UserORM).where(UserORM.email == req.email))).scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=409, detail="A user already exists with this email")

    user = UserORM(
        email=req.email,
        hashed_password=req.hashed_password,
        full_name=req.full_name,
        phone=req.phone,
        role=UserRole.STAFF,
        is_owner=False,
        is_active=True,
        household_id=None,
    )
    db.add(user)
    req.status = StaffRequestStatus.APPROVED
    req.reviewed_by = admin_user.id
    req.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "approved", "created_user_email": user.email}


@app.post("/api/admin/create-admin")
async def create_admin(
    user_data: UserCreate,
    x_dev_secret: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
    admin_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    """
    Owner-only in prod.
    Dev-mode bypass supported with header: X-Dev-Secret: <DEV_ADMIN_SECRET>
    """
    await require_owner_or_dev(x_dev_secret, admin_user)

    existing = (await db.execute(select(UserORM).where(UserORM.email == user_data.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = UserORM(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        role=UserRole.ADMIN,
        is_owner=False,
        is_active=True,
        household_id=None,
    )
    db.add(user)
    await db.commit()
    return {"status": "created", "email": user.email}


@app.get("/api/admin/is-owner/{user_id}")
async def is_owner(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    u = (await db.execute(select(UserORM).where(UserORM.id == user_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": u.id, "email": u.email, "is_owner": bool(u.is_owner)}

# ---------------- ADMIN CUSTOMER MANAGEMENT ----------------

@app.get("/api/admin/users")
async def list_users(
    role: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    admin_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    stmt = select(UserORM)

    if role:
        try:
            stmt = stmt.where(UserORM.role == UserRole(role))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid role")

    res = await db.execute(stmt)
    users = res.scalars().all()

    items = []
    for u in users:
        if search:
            q = search.lower()
            if q not in (u.email or "").lower() and q not in (u.full_name or "").lower():
                continue

        items.append({
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "phone": u.phone,
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "is_active": u.is_active,
            "is_owner": u.is_owner,
            "household_id": u.household_id,
            "created_at": u.created_at,
            "address": getattr(u, "address", None),
            "city": getattr(u, "city", None),
            "state": getattr(u, "state", None),
            "zip_code": getattr(u, "zip_code", None),
            "emergency_contact": getattr(u, "emergency_contact", None),
            "emergency_phone": getattr(u, "emergency_phone", None),
            "notes": getattr(u, "notes", None),
        })

    return items


@app.post("/api/admin/users/staff")
async def create_staff_user(
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    full_name = (data.get("full_name") or "").strip()
    phone = (data.get("phone") or "").strip() or None
    location_id = (data.get("location_id") or "").strip() or None
    is_active = bool(data.get("is_active", True))

    if not email or not password or not full_name:
        raise HTTPException(status_code=400, detail="full_name, email, and password are required")

    existing = (await db.execute(select(UserORM).where(UserORM.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    if location_id:
        location = (await db.execute(select(LocationORM).where(LocationORM.id == location_id))).scalar_one_or_none()
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")

    user = UserORM(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        phone=phone,
        role=UserRole.STAFF,
        location_id=location_id,
        is_active=is_active,
        is_owner=False,
        household_id=None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "location_id": user.location_id,
        "is_active": user.is_active,
        "created_at": user.created_at,
    }


@app.patch("/api/admin/users/{user_id}")
async def update_staff_user(
    user_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    user = (await db.execute(select(UserORM).where(UserORM.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role != UserRole.STAFF:
        raise HTTPException(status_code=400, detail="Target user is not staff")

    if "email" in data and data["email"]:
        email = str(data["email"]).strip().lower()
        existing = (await db.execute(select(UserORM).where(UserORM.email == email, UserORM.id != user_id))).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = email

    if "full_name" in data and data["full_name"] is not None:
        user.full_name = str(data["full_name"]).strip()

    if "phone" in data:
        user.phone = str(data["phone"]).strip() or None

    if "location_id" in data:
        location_id = str(data["location_id"]).strip() if data["location_id"] is not None else ""
        location_id = location_id or None
        if location_id:
            location = (await db.execute(select(LocationORM).where(LocationORM.id == location_id))).scalar_one_or_none()
            if not location:
                raise HTTPException(status_code=404, detail="Location not found")
        user.location_id = location_id

    if "is_active" in data:
        user.is_active = bool(data["is_active"])

    if "password" in data and data["password"]:
        user.hashed_password = hash_password(data["password"])

    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "location_id": user.location_id,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


@app.get("/api/dogs")
async def list_dogs(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.CUSTOMER, UserRole.STAFF, UserRole.ADMIN)),
):
    stmt = select(DogORM)

    if current_user.role == UserRole.CUSTOMER:
        stmt = stmt.where(DogORM.household_id == current_user.household_id)

    res = await db.execute(stmt)
    dogs = res.scalars().all()

    return [
        {
            "id": d.id,
            "name": d.name,
            "breed": d.breed,
            "age": d.age,
            "weight": d.weight,
            "household_id": d.household_id,
            "photo_url": d.photo_url,
            "gender": d.gender,
            "color": d.color,
            "birthday": d.birthday,
            "meal_routine": d.meal_routine,
            "medication_requirements": d.medication_requirements,
            "allergies": d.allergies,
            "friendly_to_cats": d.friendly_to_cats,
            "friendly_with_dogs": d.friendly_with_dogs,
            "seizure_activity": d.seizure_activity,
            "afraid_of_thunder": d.afraid_of_thunder,
            "afraid_of_fireworks": d.afraid_of_fireworks,
            "resource_guarding": d.resource_guarding,
            "fence_aggression": d.fence_aggression,
            "incidents_of_aggression": d.incidents_of_aggression,
            "other_notes": d.other_notes,
            "created_at": d.created_at,
            "updated_at": d.updated_at,
        }
        for d in dogs
    ]




@app.get("/api/dogs/{dog_id}")
async def get_dog(
    dog_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.CUSTOMER, UserRole.STAFF, UserRole.ADMIN)),
):
    dog = await db.get(DogORM, dog_id)
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    if current_user.role == UserRole.CUSTOMER and dog.household_id != current_user.household_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this dog")

    return dog


@app.patch("/api/dogs/{dog_id}")
async def update_dog(
    dog_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.CUSTOMER, UserRole.STAFF, UserRole.ADMIN)),
):
    dog = await db.get(DogORM, dog_id)
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    if current_user.role == UserRole.CUSTOMER and dog.household_id != current_user.household_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    for k, v in data.items():
        if hasattr(dog, k):
            setattr(dog, k, v)

    await db.commit()
    await db.refresh(dog)
    return dog


@app.delete("/api/dogs/{dog_id}")
async def delete_dog(
    dog_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.CUSTOMER, UserRole.ADMIN)),
):
    dog = await db.get(DogORM, dog_id)
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    if current_user.role == UserRole.CUSTOMER and dog.household_id != current_user.household_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await db.delete(dog)
    await db.commit()
    return {"ok": True}


@app.post("/api/dogs")
async def create_dog_compat(

    data: dict,
    current_user = Depends(require_role(UserRole.CUSTOMER)),
    db: AsyncSession = Depends(get_db),
):
    raw_birthday = data.get("birthday")
    birthday_value = None
    if raw_birthday:
        if isinstance(raw_birthday, str):
            try:
                birthday_value = datetime.fromisoformat(raw_birthday)
            except ValueError:
                try:
                    birthday_value = datetime.fromisoformat(f"{raw_birthday}T00:00:00")
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid birthday format")
        else:
            birthday_value = raw_birthday

    dog = DogORM(
        id=str(uuid.uuid4()),
        household_id=current_user.household_id,
        name=data.get("name"),
        breed=data.get("breed"),
        age=data.get("age"),
        weight=data.get("weight"),
        photo_url=data.get("photo_url"),
        vaccination_file_url=data.get("vaccination_file_url"),
        behavioral_notes=(
            data.get("behavioral_notes")
            or data.get("behavior_notes")
            or data.get("other_notes")
        ),
        medical_flags=[],
        internal_notes=None,
        gender=data.get("gender") or data.get("sex"),
        color=data.get("color"),
        birthday=birthday_value,
        meal_routine=data.get("meal_routine"),
        medication_requirements=data.get("medication_requirements") or data.get("medications"),
        allergies=data.get("allergies"),
        friendly_to_cats=data.get("friendly_to_cats"),
        friendly_with_dogs=data.get("friendly_with_dogs"),
        seizure_activity=data.get("seizure_activity"),
        afraid_of_thunder=data.get("afraid_of_thunder"),
        afraid_of_fireworks=data.get("afraid_of_fireworks"),
        resource_guarding=data.get("resource_guarding"),
        fence_aggression=data.get("fence_aggression"),
        incidents_of_aggression=data.get("incidents_of_aggression"),
        other_notes=data.get("other_notes"),
        vaccinations=[],
    )
    db.add(dog)
    await db.commit()
    await db.refresh(dog)
    return {
        "id": dog.id,
        "household_id": dog.household_id,
        "name": dog.name,
        "breed": dog.breed,
        "age": dog.age,
        "weight": dog.weight,
        "photo_url": dog.photo_url,
        "vaccination_file_url": dog.vaccination_file_url,
        "behavioral_notes": dog.behavioral_notes,
        "medical_flags": dog.medical_flags,
        "internal_notes": dog.internal_notes,
        "gender": dog.gender,
        "color": dog.color,
        "birthday": dog.birthday,
        "meal_routine": dog.meal_routine,
        "medication_requirements": dog.medication_requirements,
        "allergies": dog.allergies,
        "friendly_to_cats": dog.friendly_to_cats,
        "friendly_with_dogs": dog.friendly_with_dogs,
        "seizure_activity": dog.seizure_activity,
        "afraid_of_thunder": dog.afraid_of_thunder,
        "afraid_of_fireworks": dog.afraid_of_fireworks,
        "resource_guarding": dog.resource_guarding,
        "fence_aggression": dog.fence_aggression,
        "incidents_of_aggression": dog.incidents_of_aggression,
        "other_notes": dog.other_notes,
        "vaccinations": dog.vaccinations,
        "created_at": dog.created_at,
        "updated_at": dog.updated_at,
    }


@app.post("/api/admin/customers")
async def create_customer(
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    full_name = (data.get("full_name") or "").strip()
    phone = data.get("phone")
    is_active = data.get("is_active", True)

    if not email or not password or not full_name:
        raise HTTPException(status_code=400, detail="full_name, email, and password are required")

    existing = (await db.execute(select(UserORM).where(UserORM.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    household_id = os.urandom(16).hex()

    user = UserORM(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        phone=phone,
        role=UserRole.CUSTOMER,
        is_active=bool(is_active),
        is_owner=False,
        household_id=household_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "role": user.role.value,
        "is_active": user.is_active,
        "household_id": user.household_id,
    }


@app.patch("/api/admin/customers/{customer_id}")
async def update_customer(
    customer_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    customer = (await db.execute(select(UserORM).where(UserORM.id == customer_id))).scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if customer.role != UserRole.CUSTOMER:
        raise HTTPException(status_code=400, detail="Target user is not a customer")

    for field in ["full_name", "phone"]:
        if field in data:
            setattr(customer, field, data[field])

    if "is_active" in data:
        customer.is_active = bool(data["is_active"])

    if "password" in data and data["password"]:
        customer.hashed_password = hash_password(data["password"])

    await db.commit()
    await db.refresh(customer)

    return {
        "id": customer.id,
        "email": customer.email,
        "full_name": customer.full_name,
        "phone": customer.phone,
        "role": customer.role.value,
        "is_active": customer.is_active,
        "household_id": customer.household_id,
    }


@app.patch("/api/admin/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    status: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    admin_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    user = (await db.execute(select(UserORM).where(UserORM.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    next_active = None

    if is_active is not None:
        next_active = bool(is_active)
    elif status is not None:
        normalized = str(status).strip().lower()
        if normalized not in {"active", "inactive"}:
            raise HTTPException(status_code=400, detail="status must be active or inactive")
        next_active = normalized == "active"
    else:
        raise HTTPException(status_code=400, detail="status or is_active is required")

    user.is_active = next_active
    await db.commit()
    await db.refresh(user)

    return {
        "message": "User status updated",
        "id": user.id,
        "is_active": user.is_active,
        "status": "active" if user.is_active else "inactive",
    }


@app.delete("/api/admin/customers/{customer_id}")
async def deactivate_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    customer = (await db.execute(select(UserORM).where(UserORM.id == customer_id))).scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if customer.role != UserRole.CUSTOMER:
        raise HTTPException(status_code=400, detail="Target user is not a customer")

    customer.is_active = False
    await db.commit()

    return {"message": "Customer deactivated", "id": customer.id}


# ---------------- LOCATIONS ----------------

@app.get("/api/locations")
async def list_locations(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.CUSTOMER, UserRole.STAFF, UserRole.ADMIN)),
):
    res = await db.execute(select(LocationORM))
    locations = res.scalars().all()

    return [
        {
            "id": l.id,
            "name": l.name,
            "address": l.address,
            "capacity": l.capacity,
            "contact_email": l.contact_email,
            "contact_phone": l.contact_phone,
            "created_at": l.created_at,
            "updated_at": l.updated_at,
        }
        for l in locations
    ]


# ---------------- BOOKINGS ----------------

def _serialize_booking(b: BookingORM):
    return {
        "id": b.id,
        "household_id": b.household_id,
        "location_id": b.location_id,
        "accommodation_type": b.accommodation_type.value if hasattr(b.accommodation_type, "value") else str(b.accommodation_type),
        "check_in_date": b.check_in_date,
        "check_out_date": b.check_out_date,
        "status": b.status.value if hasattr(b.status, "value") else str(b.status),
        "total_price": b.total_price,
        "notes": b.notes,
        "special_request": b.special_request,
        "payment_status": b.payment_status,
        "payment_intent_id": b.payment_intent_id,
        "payment_type": b.payment_type,
        "is_holiday_pricing": b.is_holiday_pricing,
        "needs_separate_playtime": b.needs_separate_playtime,
        "separate_playtime_fee": b.separate_playtime_fee,
        "items_checklist": b.items_checklist,
        "checked_in_at": b.checked_in_at,
        "checked_out_at": b.checked_out_at,
        "customer_id": b.customer_id,
        "created_by": b.created_by,
        "modification_reason": b.modification_reason,
        "dog_ids": b.dog_ids or [],
        "created_at": b.created_at,
        "updated_at": b.updated_at,
    }


def _parse_booking_status(value: str) -> BookingStatus:
    try:
        return BookingStatus(value)
    except Exception:
        allowed = ", ".join([s.value for s in BookingStatus])
        raise HTTPException(status_code=400, detail=f"Invalid booking status. Allowed: {allowed}")


def _parse_accommodation_type(value: str) -> AccommodationType:
    try:
        return AccommodationType(value)
    except Exception:
        allowed = ", ".join([a.value for a in AccommodationType])
        raise HTTPException(status_code=400, detail=f"Invalid accommodation_type. Allowed: {allowed}")


@app.get("/api/bookings")
async def list_bookings(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.CUSTOMER, UserRole.STAFF, UserRole.ADMIN)),
):
    stmt = select(BookingORM)

    if current_user.role == UserRole.CUSTOMER:
        stmt = stmt.where(BookingORM.household_id == current_user.household_id)

    res = await db.execute(stmt)
    bookings = res.scalars().all()

    return [_serialize_booking(b) for b in bookings]


@app.post("/api/bookings")
async def create_booking_customer(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.CUSTOMER)),
):
    dog_ids = data.get("dog_ids") or []
    location_id = data.get("location_id")
    check_in_date = data.get("check_in_date")
    check_out_date = data.get("check_out_date")
    accommodation_type = data.get("accommodation_type", "room")

    if not dog_ids or not location_id or not check_in_date or not check_out_date:
        raise HTTPException(status_code=400, detail="dog_ids, location_id, check_in_date, and check_out_date are required")

    dogs_res = await db.execute(
        select(DogORM).where(DogORM.id.in_(dog_ids))
    )
    dogs = dogs_res.scalars().all()
    if len(dogs) != len(dog_ids):
        raise HTTPException(status_code=400, detail="One or more dogs were not found")

    for dog in dogs:
        if dog.household_id != current_user.household_id:
            raise HTTPException(status_code=403, detail="You can only book your own dogs")

    location = (await db.execute(select(LocationORM).where(LocationORM.id == location_id))).scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    booking = BookingORM(
        household_id=current_user.household_id,
        location_id=location_id,
        accommodation_type=_parse_accommodation_type(accommodation_type),
        check_in_date=datetime.fromisoformat(check_in_date.replace("Z", "+00:00")),
        check_out_date=datetime.fromisoformat(check_out_date.replace("Z", "+00:00")),
        status=BookingStatus.PENDING,
        total_price=float(data.get("total_price", 0.0)),
        notes=data.get("notes"),
        special_request=data.get("special_request"),
        payment_status=data.get("payment_status", "pending"),
        payment_type=data.get("payment_type", "invoice"),
        is_holiday_pricing=bool(data.get("is_holiday_pricing", False)),
        needs_separate_playtime=bool(data.get("needs_separate_playtime", False)),
        separate_playtime_fee=float(data.get("separate_playtime_fee", 0.0)),
        items_checklist=data.get("items_checklist"),
        customer_id=current_user.id,
        created_by=current_user.id,
        dog_ids=dog_ids,
    )

    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    return _serialize_booking(booking)


@app.post("/api/bookings/admin")
async def create_booking_admin(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    dog_ids = data.get("dog_ids") or []
    location_id = data.get("location_id")
    check_in_date = data.get("check_in_date")
    check_out_date = data.get("check_out_date")
    accommodation_type = data.get("accommodation_type", "room")
    customer_id = data.get("customer_id")

    if not dog_ids or not location_id or not check_in_date or not check_out_date:
        raise HTTPException(status_code=400, detail="dog_ids, location_id, check_in_date, and check_out_date are required")

    location = (await db.execute(select(LocationORM).where(LocationORM.id == location_id))).scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    dogs_res = await db.execute(
        select(DogORM).where(DogORM.id.in_(dog_ids))
    )
    dogs = dogs_res.scalars().all()
    if len(dogs) != len(dog_ids):
        raise HTTPException(status_code=400, detail="One or more dogs were not found")

    household_ids = {d.household_id for d in dogs}
    if len(household_ids) != 1:
        raise HTTPException(status_code=400, detail="All dogs on a booking must belong to the same household")

    household_id = next(iter(household_ids))

    if customer_id:
        customer = (await db.execute(select(UserORM).where(UserORM.id == customer_id))).scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        if customer.role != UserRole.CUSTOMER:
            raise HTTPException(status_code=400, detail="customer_id must reference a customer")
        if customer.household_id != household_id:
            raise HTTPException(status_code=400, detail="customer_id does not match the dogs' household")
    else:
        customer = (await db.execute(select(UserORM).where(UserORM.household_id == household_id))).scalar_one_or_none()
        customer_id = customer.id if customer else None

    booking = BookingORM(
        household_id=household_id,
        location_id=location_id,
        accommodation_type=_parse_accommodation_type(accommodation_type),
        check_in_date=datetime.fromisoformat(check_in_date.replace("Z", "+00:00")),
        check_out_date=datetime.fromisoformat(check_out_date.replace("Z", "+00:00")),
        status=BookingStatus.PENDING,
        total_price=float(data.get("total_price", 0.0)),
        notes=data.get("notes"),
        special_request=data.get("special_request"),
        payment_status=data.get("payment_status", "pending"),
        payment_type=data.get("payment_type", "invoice"),
        is_holiday_pricing=bool(data.get("is_holiday_pricing", False)),
        needs_separate_playtime=bool(data.get("needs_separate_playtime", False)),
        separate_playtime_fee=float(data.get("separate_playtime_fee", 0.0)),
        items_checklist=data.get("items_checklist"),
        customer_id=customer_id,
        created_by=current_user.id,
        dog_ids=dog_ids,
    )

    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    return _serialize_booking(booking)



@app.get("/api/bookings/{booking_id}")
async def get_booking(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.CUSTOMER, UserRole.STAFF, UserRole.ADMIN)),
):
    booking = (await db.execute(select(BookingORM).where(BookingORM.id == booking_id))).scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if current_user.role == UserRole.CUSTOMER and booking.household_id != current_user.household_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return _serialize_booking(booking)


@app.post("/api/bookings/{booking_id}/cancel")
async def cancel_booking(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.CUSTOMER, UserRole.STAFF, UserRole.ADMIN)),
):
    booking = (await db.execute(select(BookingORM).where(BookingORM.id == booking_id))).scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.status = BookingStatus.CANCELLED
    await db.commit()
    await db.refresh(booking)

    return _serialize_booking(booking)


@app.patch("/api/bookings/{booking_id}/items")
async def update_booking_items(
    booking_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    booking = (await db.execute(select(BookingORM).where(BookingORM.id == booking_id))).scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if "items_checklist" in data:
        booking.items_checklist = data["items_checklist"]

    await db.commit()
    await db.refresh(booking)

    return _serialize_booking(booking)


@app.patch("/api/bookings/{booking_id}")
async def update_booking(

    booking_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    booking = (await db.execute(select(BookingORM).where(BookingORM.id == booking_id))).scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if "location_id" in data:
        location = (await db.execute(select(LocationORM).where(LocationORM.id == data["location_id"]))).scalar_one_or_none()
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")
        booking.location_id = data["location_id"]

    if "dog_ids" in data:
        dog_ids = data["dog_ids"] or []
        dogs_res = await db.execute(select(DogORM).where(DogORM.id.in_(dog_ids)))
        dogs = dogs_res.scalars().all()
        if len(dogs) != len(dog_ids):
            raise HTTPException(status_code=400, detail="One or more dogs were not found")
        household_ids = {d.household_id for d in dogs}
        if len(household_ids) != 1:
            raise HTTPException(status_code=400, detail="All dogs on a booking must belong to the same household")
        booking.dog_ids = dog_ids
        booking.household_id = next(iter(household_ids))

    if "accommodation_type" in data:
        booking.accommodation_type = _parse_accommodation_type(data["accommodation_type"])

    if "check_in_date" in data and data["check_in_date"]:
        booking.check_in_date = datetime.fromisoformat(data["check_in_date"].replace("Z", "+00:00"))

    if "check_out_date" in data and data["check_out_date"]:
        booking.check_out_date = datetime.fromisoformat(data["check_out_date"].replace("Z", "+00:00"))

    if "total_price" in data:
        booking.total_price = float(data["total_price"])

    for field in [
        "notes",
        "special_request",
        "payment_status",
        "payment_intent_id",
        "payment_type",
        "items_checklist",
        "customer_id",
        "modification_reason",
    ]:
        if field in data:
            setattr(booking, field, data[field])

    for field in [
        "is_holiday_pricing",
        "needs_separate_playtime",
    ]:
        if field in data:
            setattr(booking, field, bool(data[field]))

    if "separate_playtime_fee" in data:
        booking.separate_playtime_fee = float(data["separate_playtime_fee"])

    await db.commit()
    await db.refresh(booking)

    return _serialize_booking(booking)


@app.patch("/api/bookings/{booking_id}/status")
async def update_booking_status(
    booking_id: str,
    status: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    booking = (await db.execute(select(BookingORM).where(BookingORM.id == booking_id))).scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    new_status = _parse_booking_status(status)
    booking.status = new_status

    now = datetime.now(timezone.utc)
    if new_status == BookingStatus.CHECKED_IN:
        booking.checked_in_at = now
    if new_status == BookingStatus.CHECKED_OUT:
        booking.checked_out_at = now

    await db.commit()
    await db.refresh(booking)

    return _serialize_booking(booking)


@app.delete("/api/bookings/{booking_id}")
async def delete_booking(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    booking = (await db.execute(select(BookingORM).where(BookingORM.id == booking_id))).scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    await db.delete(booking)
    await db.commit()

    return {"message": "Booking deleted", "id": booking_id}


# ---------------- TASKS ----------------

def _serialize_task(t: TaskORM):
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "assigned_to": t.assigned_to,
        "location_id": t.location_id,
        "due_date": t.due_date,
        "status": t.status.value if hasattr(t.status, "value") else str(t.status),
        "completed_at": t.completed_at,
        "completed_by": t.completed_by,
        "completed_by_name": t.completed_by_name,
        "checklist_items": t.checklist_items or [],
        "form_template_id": getattr(t, "form_template_id", None),
        "require_form_completion": getattr(t, "require_form_completion", False),
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


def _parse_task_status(value: str) -> TaskStatus:
    try:
        return TaskStatus(value)
    except Exception:
        allowed = ", ".join([s.value for s in TaskStatus])
        raise HTTPException(status_code=400, detail=f"Invalid task status. Allowed: {allowed}")


@app.get("/api/tasks")
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    stmt = select(TaskORM)

    if current_user.role == UserRole.STAFF:
        stmt = stmt.where(
            (TaskORM.assigned_to == current_user.id) | (TaskORM.assigned_to.is_(None))
        )

    res = await db.execute(stmt.order_by(TaskORM.created_at.desc()))
    tasks = res.scalars().all()
    return [_serialize_task(t) for t in tasks]


@app.post("/api/tasks")
async def create_task(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    title = (data.get("title") or "").strip()
    location_id = (data.get("location_id") or "").strip() or getattr(current_user, "location_id", None)

    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    if not location_id:
        first_location = (await db.execute(
            select(LocationORM).order_by(LocationORM.created_at.asc())
        )).scalars().first()
        if first_location:
            location_id = first_location.id

    if not location_id:
        raise HTTPException(status_code=400, detail="location_id is required")

    location = (await db.execute(
        select(LocationORM).where(LocationORM.id == location_id)
    )).scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    assigned_to = (data.get("assigned_to") or "").strip() or None
    if assigned_to:
        assigned_user = (await db.execute(
            select(UserORM).where(UserORM.id == assigned_to)
        )).scalar_one_or_none()
        if not assigned_user:
            raise HTTPException(status_code=404, detail="Assigned user not found")

    due_date = None
    if data.get("due_date"):
        due_date = datetime.fromisoformat(str(data["due_date"]).replace("Z", "+00:00"))

    task = TaskORM(
        title=title,
        description=data.get("description"),
        assigned_to=assigned_to,
        location_id=location_id,
        due_date=due_date,
        status=_parse_task_status(data.get("status", "pending")),
        checklist_items=data.get("checklist_items") or [],

        form_template_id=data.get("form_template_id"),
        require_form_completion=bool(data.get("require_form_completion", False)),
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    return _serialize_task(task)


@app.patch("/api/tasks/{task_id}")
async def update_task(
    task_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    task = (await db.execute(
        select(TaskORM).where(TaskORM.id == task_id)
    )).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")


    # === FORM ENFORCEMENT (ON COMPLETE ONLY) ===
    if getattr(task, "require_form_completion", False) and getattr(task, "form_template_id", None):
        from db_models import FormSubmissionORM

        result = await db.execute(
            select(FormSubmissionORM).where(
                FormSubmissionORM.related_type == "task",
                FormSubmissionORM.related_id == task.id,
                FormSubmissionORM.status.in_(["submitted", "approved"])
            )
        )
        submission = result.scalar_one_or_none()

        if not submission:
            raise HTTPException(
                status_code=400,
                detail="Task requires completed form before completion"
            )

    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            raise HTTPException(status_code=400, detail="title cannot be empty")
        task.title = title

    if "description" in data:
        task.description = data["description"]

    if "assigned_to" in data:
        assigned_to = (data.get("assigned_to") or "").strip() or None
        if assigned_to:
            assigned_user = (await db.execute(
                select(UserORM).where(UserORM.id == assigned_to)
            )).scalar_one_or_none()
            if not assigned_user:
                raise HTTPException(status_code=404, detail="Assigned user not found")
        task.assigned_to = assigned_to

    if "checklist_items" in data:
        task.checklist_items = data["checklist_items"] or []

    if "location_id" in data:
        normalized_location_id = (data.get("location_id") or "").strip() or None
        if normalized_location_id:
            location = (await db.execute(
                select(LocationORM).where(LocationORM.id == normalized_location_id)
            )).scalar_one_or_none()
            if not location:
                raise HTTPException(status_code=404, detail="Location not found")
            task.location_id = normalized_location_id
        else:
            fallback_location_id = getattr(current_user, "location_id", None)
            if not fallback_location_id:
                first_location = (await db.execute(
                    select(LocationORM).order_by(LocationORM.created_at.asc())
                )).scalars().first()
                if first_location:
                    fallback_location_id = first_location.id

            if not fallback_location_id:
                raise HTTPException(status_code=400, detail="location_id is required")

            task.location_id = fallback_location_id

    if "form_template_id" in data:
        task.form_template_id = data.get("form_template_id")

    if "require_form_completion" in data:
        task.require_form_completion = bool(data.get("require_form_completion"))

    if "form_template_id" in data:
        task.form_template_id = data.get("form_template_id")

    if "require_form_completion" in data:
        task.require_form_completion = bool(data.get("require_form_completion"))

    if "due_date" in data:
        task.due_date = (
            datetime.fromisoformat(str(data["due_date"]).replace("Z", "+00:00"))
            if data["due_date"] else None
        )

    if "status" in data:
        task.status = _parse_task_status(data["status"])
        if task.status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now(timezone.utc)
            task.completed_by = current_user.id
            task.completed_by_name = current_user.full_name

    await db.commit()
    await db.refresh(task)

    return _serialize_task(task)



@app.patch("/api/tasks/{task_id}/complete")
async def complete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    task = (await db.execute(select(TaskORM).where(TaskORM.id == task_id))).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # === FORM ENFORCEMENT (ON COMPLETE ONLY) ===
    if getattr(task, "require_form_completion", False) and getattr(task, "form_template_id", None):
        from db_models import FormSubmissionORM

        result = await db.execute(
            select(FormSubmissionORM).where(
                FormSubmissionORM.related_type == "task",
                FormSubmissionORM.related_id == task.id,
                FormSubmissionORM.status.in_(["submitted", "approved"])
            )
        )
        submission = result.scalar_one_or_none()

        if not submission:
            raise HTTPException(
                status_code=400,
                detail="Task requires completed form before completion"
            )


    if current_user.role == UserRole.STAFF:
        task_assignee = getattr(task, "assigned_to", None)
        if task_assignee not in (None, current_user.id):
            raise HTTPException(status_code=403, detail="Not allowed to complete this task")

    try:
        task.status = TaskStatus.COMPLETED
    except Exception:
        task.status = "completed"

    if hasattr(task, "completed_at"):
        task.completed_at = datetime.now(timezone.utc)

    if hasattr(task, "completed_by"):
        task.completed_by = current_user.id

    if hasattr(task, "completed_by_name"):
        task.completed_by_name = current_user.full_name

    await db.commit()
    await db.refresh(task)

    return _serialize_task(task)


@app.delete("/api/tasks/{task_id}")
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    task = (await db.execute(
        select(TaskORM).where(TaskORM.id == task_id)
    )).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(task)
    await db.commit()

    return {"message": "Task deleted", "id": task_id}


# ---------------- SHIFTS ----------------

def _serialize_shift(s: ShiftORM):
    return {
        "id": s.id,
        "staff_id": s.staff_id,
        "staff_name": s.staff_name,
        "location_id": s.location_id,
        "start_time": s.start_time,
        "end_time": s.end_time,
        "notes": s.notes,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


@app.get("/api/shifts")
async def list_shifts(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    stmt = select(ShiftORM)

    if current_user.role == UserRole.STAFF:
        stmt = stmt.where(ShiftORM.staff_id == current_user.id)

    res = await db.execute(stmt.order_by(ShiftORM.start_time.desc()))
    shifts = res.scalars().all()
    return [_serialize_shift(s) for s in shifts]


@app.post("/api/shifts")
async def create_shift(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    staff_id = data.get("staff_id")
    location_id = data.get("location_id")
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    if not staff_id or not location_id or not start_time or not end_time:
        raise HTTPException(status_code=400, detail="staff_id, location_id, start_time, and end_time are required")

    staff_user = (await db.execute(
        select(UserORM).where(UserORM.id == staff_id)
    )).scalar_one_or_none()
    if not staff_user:
        raise HTTPException(status_code=404, detail="Staff user not found")

    if staff_user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=400, detail="staff_id must reference a staff or admin user")

    location = (await db.execute(
        select(LocationORM).where(LocationORM.id == location_id)
    )).scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    shift = ShiftORM(
        staff_id=staff_user.id,
        staff_name=staff_user.full_name,
        location_id=location_id,
        start_time=datetime.fromisoformat(str(start_time).replace("Z", "+00:00")),
        end_time=datetime.fromisoformat(str(end_time).replace("Z", "+00:00")),
        notes=data.get("notes"),
    )

    db.add(shift)
    await db.commit()
    await db.refresh(shift)

    return _serialize_shift(shift)


@app.patch("/api/shifts/{shift_id}")
async def update_shift(
    shift_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    shift = (await db.execute(
        select(ShiftORM).where(ShiftORM.id == shift_id)
    )).scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    if "staff_id" in data:
        staff_user = (await db.execute(
            select(UserORM).where(UserORM.id == data["staff_id"])
        )).scalar_one_or_none()
        if not staff_user:
            raise HTTPException(status_code=404, detail="Staff user not found")
        shift.staff_id = staff_user.id
        shift.staff_name = staff_user.full_name

    if "location_id" in data:
        location = (await db.execute(
            select(LocationORM).where(LocationORM.id == data["location_id"])
        )).scalar_one_or_none()
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")
        shift.location_id = data["location_id"]

    if "start_time" in data and data["start_time"]:
        shift.start_time = datetime.fromisoformat(str(data["start_time"]).replace("Z", "+00:00"))

    if "end_time" in data and data["end_time"]:
        shift.end_time = datetime.fromisoformat(str(data["end_time"]).replace("Z", "+00:00"))

    if "notes" in data:
        shift.notes = data["notes"]

    await db.commit()
    await db.refresh(shift)

    return _serialize_shift(shift)


@app.delete("/api/shifts/{shift_id}")
async def delete_shift(
    shift_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    shift = (await db.execute(
        select(ShiftORM).where(ShiftORM.id == shift_id)
    )).scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    await db.delete(shift)
    await db.commit()

    return {"message": "Shift deleted", "id": shift_id}


# ---------------- DASHBOARD ----------------

@app.get("/api/dashboard/stats")
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.CUSTOMER, UserRole.STAFF, UserRole.ADMIN)),
):
    def _scalar(value):
        return int(value or 0)

    customers_total = _scalar((
        await db.execute(
            select(func.count()).select_from(UserORM).where(UserORM.role == UserRole.CUSTOMER)
        )
    ).scalar())

    dogs_stmt = select(func.count()).select_from(DogORM)
    if current_user.role == UserRole.CUSTOMER:
        dogs_stmt = dogs_stmt.where(DogORM.household_id == current_user.household_id)
    dogs_total = _scalar((await db.execute(dogs_stmt)).scalar())

    bookings_total_stmt = select(func.count()).select_from(BookingORM)
    bookings_pending_stmt = select(func.count()).select_from(BookingORM).where(
        BookingORM.status == BookingStatus.PENDING
    )
    bookings_checked_in_stmt = select(func.count()).select_from(BookingORM).where(
        BookingORM.status == BookingStatus.CHECKED_IN
    )

    if current_user.role == UserRole.CUSTOMER:
        bookings_total_stmt = bookings_total_stmt.where(BookingORM.household_id == current_user.household_id)
        bookings_pending_stmt = bookings_pending_stmt.where(BookingORM.household_id == current_user.household_id)
        bookings_checked_in_stmt = bookings_checked_in_stmt.where(BookingORM.household_id == current_user.household_id)

    bookings_total = _scalar((await db.execute(bookings_total_stmt)).scalar())
    bookings_pending = _scalar((await db.execute(bookings_pending_stmt)).scalar())
    bookings_checked_in = _scalar((await db.execute(bookings_checked_in_stmt)).scalar())

    from db_models import Task as TaskORM, TaskStatus

    tasks_open_stmt = select(func.count()).select_from(TaskORM).where(
        TaskORM.status != TaskStatus.COMPLETED
    )
    if current_user.role == UserRole.STAFF:
        tasks_open_stmt = tasks_open_stmt.where(
            (TaskORM.assigned_to == current_user.id) | (TaskORM.assigned_to.is_(None))
        )
    tasks_open = _scalar((await db.execute(tasks_open_stmt)).scalar())

    return {
        "dogs_total": dogs_total,
        "bookings_total": bookings_total,
        "bookings_pending": bookings_pending,
        "bookings_checked_in": bookings_checked_in,
        "tasks_open": tasks_open,
        "customers_total": customers_total,
    }




# ---------------- AUDIT LOGS ----------------

def _serialize_audit_log(a: AuditLogORM):
    return {
        "id": a.id,
        "user_id": a.user_id,
        "action": a.action.value if hasattr(a.action, "value") else str(a.action),
        "resource_type": a.resource_type,
        "resource_id": a.resource_id,
        "details": a.details or {},
        "ip_address": a.ip_address,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }


@app.get("/api/audit-logs")
async def list_audit_logs(
    action: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    stmt = select(AuditLogORM)

    if action:
        try:
            stmt = stmt.where(AuditLogORM.action == AuditAction(action))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid action")

    stmt = stmt.order_by(AuditLogORM.created_at.desc()).limit(limit)

    res = await db.execute(stmt)
    items = res.scalars().all()
    return [_serialize_audit_log(a) for a in items]

# ==================== SCHEDULING COMPAT ROUTES ====================

@app.get("/api/scheduling/shifts")
async def get_scheduling_shifts(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    """
    Compatibility alias for frontend ScheduleViewPage.
    Returns the same shift data shape the UI expects.
    """
    stmt = select(ShiftORM)

    if current_user.role == UserRole.STAFF:
        stmt = stmt.where(ShiftORM.staff_id == current_user.id)

    if start_date is not None:
        stmt = stmt.where(ShiftORM.start_time >= start_date)

    if end_date is not None:
        stmt = stmt.where(ShiftORM.start_time <= end_date)

    res = await db.execute(stmt.order_by(ShiftORM.start_time.asc()))
    items = res.scalars().all()

    return [
        {
            "id": s.id,
            "staff_id": s.staff_id,
            "staff_name": s.staff_name,
            "location_id": s.location_id,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "notes": s.notes,
            "status": "published",
            "color": "#3B82F6",
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }
        for s in items
    ]


@app.post("/api/scheduling/shifts")
async def create_scheduling_shift(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    staff_id = payload.get("staff_id")
    location_id = (payload.get("location_id") or "").strip() or getattr(current_user, "location_id", None)
    start_time = payload.get("start_time")
    end_time = payload.get("end_time")
    notes = payload.get("notes")

    if not staff_id or not start_time or not end_time:
        raise HTTPException(status_code=400, detail="staff_id, start_time, and end_time are required")

    if not location_id:
        first_location = (await db.execute(
            select(LocationORM).order_by(LocationORM.created_at.asc())
        )).scalars().first()
        if first_location:
            location_id = first_location.id

    if not location_id:
        raise HTTPException(status_code=400, detail="location_id is required")

    staff_user = (await db.execute(select(UserORM).where(UserORM.id == staff_id))).scalar_one_or_none()
    if not staff_user:
        raise HTTPException(status_code=404, detail="Staff user not found")
    if staff_user.role != UserRole.STAFF:
        raise HTTPException(status_code=400, detail="Target user is not staff")

    location = (await db.execute(select(LocationORM).where(LocationORM.id == location_id))).scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    start_dt = datetime.fromisoformat(str(start_time).replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(str(end_time).replace("Z", "+00:00"))
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    shift = ShiftORM(
        staff_id=staff_user.id,
        staff_name=staff_user.full_name,
        location_id=location_id,
        start_time=start_dt,
        end_time=end_dt,
        notes=notes,
    )
    db.add(shift)
    await db.commit()
    await db.refresh(shift)

    return {
        "id": shift.id,
        "staff_id": shift.staff_id,
        "staff_name": shift.staff_name,
        "location_id": shift.location_id,
        "start_time": shift.start_time,
        "end_time": shift.end_time,
        "notes": shift.notes,
        "created_at": shift.created_at,
        "updated_at": shift.updated_at,
    }


@app.patch("/api/scheduling/shifts/{shift_id}")
async def update_scheduling_shift(
    shift_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    shift = (await db.execute(select(ShiftORM).where(ShiftORM.id == shift_id))).scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    if "staff_id" in payload and payload["staff_id"]:
        staff_user = (await db.execute(select(UserORM).where(UserORM.id == payload["staff_id"]))).scalar_one_or_none()
        if not staff_user:
            raise HTTPException(status_code=404, detail="Staff user not found")
        if staff_user.role != UserRole.STAFF:
            raise HTTPException(status_code=400, detail="Target user is not staff")
        shift.staff_id = staff_user.id
        shift.staff_name = staff_user.full_name

    if "location_id" in payload:
        normalized_location_id = (payload.get("location_id") or "").strip() or None
        if normalized_location_id:
            location = (await db.execute(select(LocationORM).where(LocationORM.id == normalized_location_id))).scalar_one_or_none()
            if not location:
                raise HTTPException(status_code=404, detail="Location not found")
            shift.location_id = normalized_location_id
        else:
            fallback_location_id = getattr(current_user, "location_id", None)
            if not fallback_location_id:
                first_location = (await db.execute(
                    select(LocationORM).order_by(LocationORM.created_at.asc())
                )).scalars().first()
                if first_location:
                    fallback_location_id = first_location.id

            if not fallback_location_id:
                raise HTTPException(status_code=400, detail="location_id is required")

            shift.location_id = fallback_location_id

    if "start_time" in payload and payload["start_time"]:
        shift.start_time = datetime.fromisoformat(str(payload["start_time"]).replace("Z", "+00:00"))

    if "end_time" in payload and payload["end_time"]:
        shift.end_time = datetime.fromisoformat(str(payload["end_time"]).replace("Z", "+00:00"))

    if shift.end_time <= shift.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    if "notes" in payload:
        shift.notes = payload["notes"]

    await db.commit()
    await db.refresh(shift)

    return {
        "id": shift.id,
        "staff_id": shift.staff_id,
        "staff_name": shift.staff_name,
        "location_id": shift.location_id,
        "start_time": shift.start_time,
        "end_time": shift.end_time,
        "notes": shift.notes,
        "created_at": shift.created_at,
        "updated_at": shift.updated_at,
    }


@app.delete("/api/scheduling/shifts/{shift_id}")
async def delete_scheduling_shift(
    shift_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    shift = (await db.execute(select(ShiftORM).where(ShiftORM.id == shift_id))).scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    await db.delete(shift)
    await db.commit()

    return {"message": "Shift deleted", "id": shift_id}


@app.get("/api/scheduling/swap-requests")
async def get_shift_swap_requests(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    """
    Minimal real implementation using audit_logs as storage.
    This avoids introducing a missing SwapRequest model while stopping 404s.
    """
    stmt = (
        select(AuditLogORM)
        .where(AuditLogORM.resource_type == "shift_swap_request")
        .where(AuditLogORM.user_id == current_user.id)
        .order_by(AuditLogORM.created_at.desc())
    )

    res = await db.execute(stmt)
    items = res.scalars().all()

    return [
        {
            "id": a.id,
            "shift_id": (a.details or {}).get("shift_id"),
            "target_staff_id": (a.details or {}).get("target_staff_id"),
            "reason": (a.details or {}).get("reason"),
            "status": (a.details or {}).get("status", "pending"),
            "created_at": a.created_at,
            "updated_at": a.updated_at,
        }
        for a in items
    ]


@app.post("/api/scheduling/swap-requests")
async def create_shift_swap_request(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    """
    Minimal real implementation using audit_logs as storage.
    """
    shift_id = payload.get("shift_id")
    target_staff_id = payload.get("target_staff_id")
    reason = payload.get("reason")

    if not shift_id or not target_staff_id:
        raise HTTPException(status_code=400, detail="shift_id and target_staff_id are required")

    shift = (
        await db.execute(
            select(ShiftORM).where(ShiftORM.id == shift_id)
        )
    ).scalar_one_or_none()

    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    if shift.staff_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only request swaps for your own shifts")

    audit = AuditLogORM(
        user_id=current_user.id,
        action=AuditAction.CREATE,
        resource_type="shift_swap_request",
        resource_id=shift_id,
        details={
            "shift_id": shift_id,
            "target_staff_id": target_staff_id,
            "reason": reason,
            "status": "pending",
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)

    return {
        "id": audit.id,
        "shift_id": shift_id,
        "target_staff_id": target_staff_id,
        "reason": reason,
        "status": "pending",
        "created_at": audit.created_at,
        "updated_at": audit.updated_at,
    }


# ==================== TIME ENTRY COMPAT ROUTES ====================

def _minutes_between(start_dt, end_dt):
    if not start_dt or not end_dt:
        return 0
    return max(0, int((end_dt - start_dt).total_seconds() // 60))

def _serialize_time_entry(e: TimeEntryORM):
    total_minutes = _minutes_between(e.clock_in, e.clock_out) if e.clock_out else 0
    return {
        "id": e.id,
        "staff_id": e.staff_id,
        "clock_in": e.clock_in.isoformat() if e.clock_in else None,
        "clock_out": e.clock_out.isoformat() if e.clock_out else None,
        "location_id": e.location_id,
        "notes": e.notes,
        "total_minutes": total_minutes,
        "status": "active" if e.clock_out is None else "completed",
        "on_break": False,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }

def _serialize_time_mod_request(r: TimeModificationRequestORM):
    return {
        "id": r.id,
        "time_entry_id": r.time_entry_id,
        "staff_id": r.staff_id,
        "staff_name": r.staff_name,
        "original_clock_in": r.original_clock_in,
        "original_clock_out": r.original_clock_out,
        "requested_clock_in": r.requested_clock_in,
        "requested_clock_out": r.requested_clock_out,
        "reason": r.reason,
        "status": r.status.value if hasattr(r.status, "value") else str(r.status),
        "reviewed_by": r.reviewed_by,
        "reviewed_at": r.reviewed_at,
        "review_notes": r.review_notes,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }



def _parse_k9_ops_date(date_value: str | None):
    if date_value:
        return datetime.fromisoformat(date_value.replace("Z", "+00:00")).date()
    return datetime.utcnow().date()


@app.get("/api/k9/kennels")
async def get_k9_kennels(
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return []


@app.get("/api/k9/operations/summary")
async def get_k9_operations_summary(
    location_id: str | None = Query(default=None),
    date: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    target_date = _parse_k9_ops_date(date)

    stmt = select(BookingORM)
    if location_id:
        stmt = stmt.where(BookingORM.location_id == location_id)

    res = await db.execute(stmt)
    bookings = res.scalars().all()

    on_site = [
        b for b in bookings
        if b.check_in_date.date() <= target_date <= b.check_out_date.date()
    ]
    check_ins = [b for b in bookings if b.check_in_date.date() == target_date]
    check_outs = [b for b in bookings if b.check_out_date.date() == target_date]

    return {
        "date": str(target_date),
        "location_id": location_id,
        "dogs_on_site": len(on_site),
        "active_bookings": len(on_site),
        "check_ins": len(check_ins),
        "check_outs": len(check_outs),
        "baths_due": 0,
        "kennels_occupied": len(on_site),
    }


@app.get("/api/k9/operations/dogs-on-site")
async def get_k9_operations_dogs_on_site(
    location_id: str | None = Query(default=None),
    date: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    target_date = _parse_k9_ops_date(date)

    stmt = select(BookingORM)
    if location_id:
        stmt = stmt.where(BookingORM.location_id == location_id)

    res = await db.execute(stmt)
    bookings = res.scalars().all()

    items = [
        _serialize_booking(b)
        for b in bookings
        if b.check_in_date.date() <= target_date <= b.check_out_date.date()
    ]
    return items


@app.get("/api/k9/operations/check-ins")
async def get_k9_operations_check_ins(
    location_id: str | None = Query(default=None),
    date: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    target_date = _parse_k9_ops_date(date)

    stmt = select(BookingORM)
    if location_id:
        stmt = stmt.where(BookingORM.location_id == location_id)

    res = await db.execute(stmt)
    bookings = res.scalars().all()

    items = [
        _serialize_booking(b)
        for b in bookings
        if b.check_in_date.date() == target_date
    ]
    return items


@app.get("/api/k9/operations/check-outs")
async def get_k9_operations_check_outs(
    location_id: str | None = Query(default=None),
    date: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    target_date = _parse_k9_ops_date(date)

    stmt = select(BookingORM)
    if location_id:
        stmt = stmt.where(BookingORM.location_id == location_id)

    res = await db.execute(stmt)
    bookings = res.scalars().all()

    items = [
        _serialize_booking(b)
        for b in bookings
        if b.check_out_date.date() == target_date
    ]
    return items


@app.get("/api/k9/operations/baths-due")
async def get_k9_operations_baths_due(
    location_id: str | None = Query(default=None),
    date: str | None = Query(default=None),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return []


@app.get("/api/k9/coupons")
async def get_k9_coupons(
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return []


@app.post("/api/k9/coupons")
async def create_k9_coupon(
    payload: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    return {
        "status": "not_implemented",
        "coupon": payload,
    }




@app.get("/api/admin/settings")
async def get_admin_settings_compat(
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    return {
        "booking_requires_approval": True,
    }


@app.patch("/api/admin/settings/booking_requires_approval")
async def patch_admin_settings_booking_requires_approval_compat(
    value: bool = Query(...),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    return {
        "status": "ok",
        "booking_requires_approval": value,
    }


@app.get("/api/service-types")
async def get_service_types_compat(
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return []


@app.get("/api/admin/pricing-rules")
async def get_admin_pricing_rules_compat(
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    return []


@app.get("/api/users")
async def get_users_compat(
    search: str | None = Query(default=None),
    role: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    stmt = select(UserORM)

    if role:
        try:
            stmt = stmt.where(UserORM.role == UserRole(role))
        except Exception:
            return []

    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(
            func.lower(UserORM.full_name).like(like) |
            func.lower(UserORM.email).like(like)
        )

    res = await db.execute(stmt.order_by(UserORM.created_at.desc()))
    items = res.scalars().all()

    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "status": (
                u.status.value if hasattr(u, "status") and hasattr(u.status, "value")
                else str(u.status) if hasattr(u, "status")
                else ("active" if getattr(u, "is_active", True) else "inactive")
            ),
            "location_id": u.location_id,
            "household_id": u.household_id,
            "created_at": u.created_at,
        }
        for u in items
    ]


def _serialize_time_off_request(a: AuditLogORM):
    details = a.details or {}
    return {
        "id": a.id,
        "staff_id": details.get("staff_id") or a.user_id,
        "staff_name": details.get("staff_name"),
        "start_date": details.get("start_date"),
        "end_date": details.get("end_date"),
        "reason": details.get("reason"),
        "status": details.get("status", "pending"),
        "review_notes": details.get("review_notes"),
        "created_at": a.created_at,
        "updated_at": a.updated_at,
        "reviewed_at": details.get("reviewed_at"),
    }


@app.get("/api/hr/time-off-requests")
async def get_hr_time_off_requests(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    stmt = (
        select(AuditLogORM)
        .where(AuditLogORM.resource_type == "time_off_request")
        .order_by(AuditLogORM.created_at.desc())
    )

    if current_user.role == UserRole.STAFF:
        stmt = stmt.where(AuditLogORM.user_id == current_user.id)

    res = await db.execute(stmt)
    items = res.scalars().all()
    return [_serialize_time_off_request(a) for a in items]


@app.post("/api/hr/time-off-requests")
async def create_hr_time_off_request(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    staff_id = payload.get("staff_id") or current_user.id
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    reason = payload.get("reason")

    if not start_date or not end_date:
        raise HTTPException(status_code=400, detail="start_date and end_date are required")

    if current_user.role == UserRole.STAFF and staff_id != current_user.id:
        raise HTTPException(status_code=403, detail="Staff may only create their own PTO requests")

    staff_user = (await db.execute(select(UserORM).where(UserORM.id == staff_id))).scalar_one_or_none()
    if not staff_user:
        raise HTTPException(status_code=404, detail="Staff user not found")

    audit = AuditLogORM(
        user_id=staff_id,
        action=AuditAction.CREATE,
        resource_type="time_off_request",
        resource_id=staff_id,
        details={
            "staff_id": staff_id,
            "staff_name": staff_user.full_name,
            "start_date": start_date,
            "end_date": end_date,
            "reason": reason,
            "status": "pending",
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)

    return _serialize_time_off_request(audit)


@app.patch("/api/hr/time-off-requests/{request_id}")
async def update_hr_time_off_request(
    request_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    audit = (
        await db.execute(
            select(AuditLogORM).where(
                AuditLogORM.id == request_id,
                AuditLogORM.resource_type == "time_off_request",
            )
        )
    ).scalar_one_or_none()

    if not audit:
        raise HTTPException(status_code=404, detail="Time off request not found")

    details = dict(audit.details or {})

    if "staff_id" in payload and payload["staff_id"]:
        staff_user = (await db.execute(select(UserORM).where(UserORM.id == payload["staff_id"]))).scalar_one_or_none()
        if not staff_user:
            raise HTTPException(status_code=404, detail="Staff user not found")
        details["staff_id"] = staff_user.id
        details["staff_name"] = staff_user.full_name
        audit.user_id = staff_user.id

    if "start_date" in payload and payload["start_date"]:
        details["start_date"] = payload["start_date"]

    if "end_date" in payload and payload["end_date"]:
        details["end_date"] = payload["end_date"]

    if "reason" in payload:
        details["reason"] = payload["reason"]

    if "status" in payload and payload["status"]:
        details["status"] = str(payload["status"]).strip().lower()

    if "review_notes" in payload:
        details["review_notes"] = payload["review_notes"]

    details["reviewed_at"] = datetime.now(timezone.utc).isoformat() if payload.get("status") else details.get("reviewed_at")

    audit.action = AuditAction.UPDATE
    audit.details = details

    await db.commit()
    await db.refresh(audit)

    return _serialize_time_off_request(audit)


@app.delete("/api/hr/time-off-requests/{request_id}")
async def delete_hr_time_off_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    audit = (
        await db.execute(
            select(AuditLogORM).where(
                AuditLogORM.id == request_id,
                AuditLogORM.resource_type == "time_off_request",
            )
        )
    ).scalar_one_or_none()

    if not audit:
        raise HTTPException(status_code=404, detail="Time off request not found")

    await db.delete(audit)
    await db.commit()

    return {"message": "Time off request deleted", "id": request_id}


@app.get("/api/time-off/policies")
async def list_time_off_policies(
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return []


@app.post("/api/time-off/policies")
async def create_time_off_policy(
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    raise HTTPException(status_code=501, detail="Time-off policies not implemented")


@app.patch("/api/time-off/policies/{policy_id}")
async def update_time_off_policy(
    policy_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    raise HTTPException(status_code=501, detail="Time-off policies not implemented")


@app.delete("/api/time-off/policies/{policy_id}")
async def delete_time_off_policy(
    policy_id: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    raise HTTPException(status_code=501, detail="Time-off policies not implemented")


@app.get("/api/hr/time-off-policies")
async def get_hr_time_off_policies_compat(
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return await list_time_off_policies(current_user=current_user)


@app.get("/api/k9/inventory/products")
async def get_k9_inventory_products_compat(
    active_only: bool | None = Query(default=None),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return []




@app.get("/api/admin/revenue/summary")
async def get_admin_revenue_summary_compat(
    period: str | None = Query(default="month"),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    return {
        "period": period,
        "gross_revenue": 0,
        "net_revenue": 0,
        "booking_count": 0,
        "average_booking_value": 0,
    }


@app.get("/api/admin/revenue/by-accommodation")
async def get_admin_revenue_by_accommodation_compat(
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    return []


@app.get("/api/admin/revenue/trends")
async def get_admin_revenue_trends_compat(
    period: str | None = Query(default="month"),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    return []


@app.get("/api/incidents")
async def get_incidents_compat(
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return []


@app.post("/api/incidents")
async def create_incident_compat(
    payload: dict,
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return {
        "status": "created",
        "incident": payload,
    }


@app.get("/api/schedules")
async def get_schedules_compat(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return await list_shifts(db=db, current_user=current_user)


@app.get("/api/chats")
async def get_chats_compat(
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return []


@app.get("/api/chat/users")
async def get_chat_users_compat(
    search: str | None = Query(default=None),
    role: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return await get_users_compat(search=search, role=role, db=db, current_user=current_user)



@app.get("/api/forms/templates")
async def list_form_templates(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    result = await db.execute(
        select(FormTemplateORM).order_by(FormTemplateORM.created_at.desc())
    )
    templates = result.scalars().all()

    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "location_id": t.location_id,
            "fields": t.fields or [],
            "assignable_to": t.assignable_to,
            "require_signature": t.require_signature,
            "require_gps": t.require_gps,
            "allow_save_draft": t.allow_save_draft,
            "allow_edit_after_submit": t.allow_edit_after_submit,
            "notify_on_submit": t.notify_on_submit or [],
            "is_active": t.is_active,
            "is_template": t.is_template,
            "version": t.version,
            "category": t.category,
            "tags": t.tags or [],
            "created_at": t.created_at,
            "updated_at": t.updated_at,
        }
        for t in templates
    ]


@app.post("/api/forms/templates")
async def create_form_template(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    template = FormTemplateORM(
        id=str(uuid4()),
        name=payload.get("name"),
        description=payload.get("description"),
        location_id=payload.get("location_id"),
        fields=payload.get("fields", []),
        assignable_to=payload.get("assignable_to", "all"),
        require_signature=payload.get("require_signature", False),
        require_gps=payload.get("require_gps", False),
        allow_save_draft=payload.get("allow_save_draft", True),
        allow_edit_after_submit=payload.get("allow_edit_after_submit", False),
        notify_on_submit=payload.get("notify_on_submit", []),
        is_active=payload.get("is_active", True),
        is_template=True,
        version=1,
        category=payload.get("category"),
        tags=payload.get("tags", []),
    )

    if not template.name:
        raise HTTPException(status_code=400, detail="name is required")

    db.add(template)
    await db.commit()
    await db.refresh(template)

    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "location_id": template.location_id,
        "fields": template.fields or [],
        "assignable_to": template.assignable_to,
        "require_signature": template.require_signature,
        "require_gps": template.require_gps,
        "allow_save_draft": template.allow_save_draft,
        "allow_edit_after_submit": template.allow_edit_after_submit,
        "notify_on_submit": template.notify_on_submit or [],
        "is_active": template.is_active,
        "is_template": template.is_template,
        "version": template.version,
        "category": template.category,
        "tags": template.tags or [],
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }


@app.get("/api/forms/templates/{template_id}")
async def get_form_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    template = await db.get(FormTemplateORM, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "location_id": template.location_id,
        "fields": template.fields or [],
        "assignable_to": template.assignable_to,
        "require_signature": template.require_signature,
        "require_gps": template.require_gps,
        "allow_save_draft": template.allow_save_draft,
        "allow_edit_after_submit": template.allow_edit_after_submit,
        "notify_on_submit": template.notify_on_submit or [],
        "is_active": template.is_active,
        "is_template": template.is_template,
        "version": template.version,
        "category": template.category,
        "tags": template.tags or [],
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }


@app.patch("/api/forms/templates/{template_id}")
async def update_form_template(
    template_id: str,
    updates: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    template = await db.get(FormTemplateORM, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    allowed = {
        "name",
        "description",
        "location_id",
        "fields",
        "assignable_to",
        "require_signature",
        "require_gps",
        "allow_save_draft",
        "allow_edit_after_submit",
        "notify_on_submit",
        "is_active",
        "category",
        "tags",
    }

    changed = False
    for key, value in updates.items():
        if key in allowed:
            setattr(template, key, value)
            changed = True

    if changed:
        template.version = (template.version or 1) + 1

    await db.commit()
    await db.refresh(template)

    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "location_id": template.location_id,
        "fields": template.fields or [],
        "assignable_to": template.assignable_to,
        "require_signature": template.require_signature,
        "require_gps": template.require_gps,
        "allow_save_draft": template.allow_save_draft,
        "allow_edit_after_submit": template.allow_edit_after_submit,
        "notify_on_submit": template.notify_on_submit or [],
        "is_active": template.is_active,
        "is_template": template.is_template,
        "version": template.version,
        "category": template.category,
        "tags": template.tags or [],
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }


@app.get("/api/forms/submissions")
async def list_form_submissions(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    stmt = select(FormSubmissionORM).order_by(FormSubmissionORM.created_at.desc())

    if current_user.role == UserRole.STAFF:
        stmt = stmt.where(FormSubmissionORM.staff_id == current_user.id)

    result = await db.execute(stmt)
    submissions = result.scalars().all()

    return [
        {
            "id": s.id,
            "template_id": s.template_id,
            "staff_id": s.staff_id,
            "staff_name": s.staff_name,
            "location_id": s.location_id,
            "values": s.values or {},
            "attachments": s.attachments or [],
            "signature_data": s.signature_data,
            "gps_latitude": s.gps_latitude,
            "gps_longitude": s.gps_longitude,
            "gps_accuracy": s.gps_accuracy,
            "status": s.status,
            "submitted_at": s.submitted_at,
            "reviewed_by": s.reviewed_by,
            "reviewed_at": s.reviewed_at,
            "review_notes": s.review_notes,
            "related_type": s.related_type,
            "related_id": s.related_id,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }
        for s in submissions
    ]


@app.post("/api/forms/submissions")
async def create_form_submission(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    template_id = payload.get("template_id")
    if not template_id:
        raise HTTPException(status_code=400, detail="template_id is required")

    template = await db.get(FormTemplateORM, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    status = payload.get("status", "draft")
    submitted_at = datetime.utcnow() if status == "submitted" else None

    submission = FormSubmissionORM(
        template_id=template_id,
        staff_id=current_user.id,
        staff_name=getattr(current_user, "full_name", None),
        location_id=payload.get("location_id") or getattr(current_user, "location_id", None),
        values=payload.get("values", {}),
        attachments=payload.get("attachments", []),
        signature_data=payload.get("signature_data"),
        gps_latitude=payload.get("gps_latitude"),
        gps_longitude=payload.get("gps_longitude"),
        gps_accuracy=payload.get("gps_accuracy"),
        status=status,
        submitted_at=submitted_at,
        related_type=payload.get("related_type"),
        related_id=payload.get("related_id"),
    )

    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    return {
        "id": submission.id,
        "template_id": submission.template_id,
        "staff_id": submission.staff_id,
        "staff_name": submission.staff_name,
        "location_id": submission.location_id,
        "values": submission.values or {},
        "attachments": submission.attachments or [],
        "signature_data": submission.signature_data,
        "gps_latitude": submission.gps_latitude,
        "gps_longitude": submission.gps_longitude,
        "gps_accuracy": submission.gps_accuracy,
        "status": submission.status,
        "submitted_at": submission.submitted_at,
        "reviewed_by": submission.reviewed_by,
        "reviewed_at": submission.reviewed_at,
        "review_notes": submission.review_notes,
        "related_type": submission.related_type,
        "related_id": submission.related_id,
        "created_at": submission.created_at,
        "updated_at": submission.updated_at,
    }


@app.get("/api/forms/submissions/{submission_id}")
async def get_form_submission(
    submission_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    submission = await db.get(FormSubmissionORM, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if current_user.role == UserRole.STAFF and submission.staff_id != current_user.id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    return {
        "id": submission.id,
        "template_id": submission.template_id,
        "staff_id": submission.staff_id,
        "staff_name": submission.staff_name,
        "location_id": submission.location_id,
        "values": submission.values or {},
        "attachments": submission.attachments or [],
        "signature_data": submission.signature_data,
        "gps_latitude": submission.gps_latitude,
        "gps_longitude": submission.gps_longitude,
        "gps_accuracy": submission.gps_accuracy,
        "status": submission.status,
        "submitted_at": submission.submitted_at,
        "reviewed_by": submission.reviewed_by,
        "reviewed_at": submission.reviewed_at,
        "review_notes": submission.review_notes,
        "related_type": submission.related_type,
        "related_id": submission.related_id,
        "created_at": submission.created_at,
        "updated_at": submission.updated_at,
    }


@app.patch("/api/forms/submissions/{submission_id}")
async def update_form_submission(
    submission_id: str,
    updates: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    submission = await db.get(FormSubmissionORM, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if current_user.role == UserRole.STAFF and submission.staff_id != current_user.id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    allowed = {
        "values",
        "attachments",
        "signature_data",
        "gps_latitude",
        "gps_longitude",
        "gps_accuracy",
        "status",
        "related_type",
        "related_id",
        "location_id",
    }

    for key, value in updates.items():
        if key in allowed:
            setattr(submission, key, value)

    if updates.get("status") == "submitted" and not submission.submitted_at:
        submission.submitted_at = datetime.utcnow()

    await db.commit()
    await db.refresh(submission)

    return {
        "id": submission.id,
        "template_id": submission.template_id,
        "staff_id": submission.staff_id,
        "staff_name": submission.staff_name,
        "location_id": submission.location_id,
        "values": submission.values or {},
        "attachments": submission.attachments or [],
        "signature_data": submission.signature_data,
        "gps_latitude": submission.gps_latitude,
        "gps_longitude": submission.gps_longitude,
        "gps_accuracy": submission.gps_accuracy,
        "status": submission.status,
        "submitted_at": submission.submitted_at,
        "reviewed_by": submission.reviewed_by,
        "reviewed_at": submission.reviewed_at,
        "review_notes": submission.review_notes,
        "related_type": submission.related_type,
        "related_id": submission.related_id,
        "created_at": submission.created_at,
        "updated_at": submission.updated_at,
    }


@app.post("/api/forms/submissions/{submission_id}/review")
async def review_form_submission(
    submission_id: str,
    status: str,
    notes: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    submission = await db.get(FormSubmissionORM, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission.status = status
    submission.review_notes = notes
    submission.reviewed_by = current_user.id
    submission.reviewed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(submission)

    return {
        "id": submission.id,
        "template_id": submission.template_id,
        "staff_id": submission.staff_id,
        "staff_name": submission.staff_name,
        "location_id": submission.location_id,
        "values": submission.values or {},
        "attachments": submission.attachments or [],
        "signature_data": submission.signature_data,
        "gps_latitude": submission.gps_latitude,
        "gps_longitude": submission.gps_longitude,
        "gps_accuracy": submission.gps_accuracy,
        "status": submission.status,
        "submitted_at": submission.submitted_at,
        "reviewed_by": submission.reviewed_by,
        "reviewed_at": submission.reviewed_at,
        "review_notes": submission.review_notes,
        "related_type": submission.related_type,
        "related_id": submission.related_id,
        "created_at": submission.created_at,
        "updated_at": submission.updated_at,
    }


@app.get("/api/forms/analytics/submissions")
async def get_forms_analytics_submissions_compat(
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return []


@app.get("/api/forms/task-templates")
async def get_forms_task_templates_compat(
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return []


@app.get("/api/forms/analytics/tasks")
async def get_forms_analytics_tasks_compat(
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return []


@app.get("/api/k9/bookings/pending-approval")
async def get_k9_bookings_pending_approval_compat(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    stmt = select(BookingORM).where(BookingORM.status == BookingStatus.PENDING).order_by(BookingORM.created_at.desc())
    res = await db.execute(stmt)
    items = res.scalars().all()
    return [_serialize_booking(b) for b in items]


@app.get("/api/k9/inventory/low-stock")
async def get_k9_inventory_low_stock_compat(
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return []


@app.post("/api/hr/time-off-requests")
async def post_hr_time_off_requests_compat(
    payload: dict,
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return {
        "status": "accepted",
        "request": payload,
    }


@app.post("/api/k9/kennels")
async def post_k9_kennels_compat(
    payload: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    return {
        "status": "created",
        "kennel": payload,
    }


@app.post("/api/k9/inventory/products")
async def post_k9_inventory_products_compat(
    payload: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    return {
        "status": "created",
        "product": payload,
    }


@app.get("/api/time-entries")
async def get_time_entries(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    stmt = select(TimeEntryORM)

    if current_user.role == UserRole.STAFF:
        stmt = stmt.where(TimeEntryORM.staff_id == current_user.id)

    res = await db.execute(stmt.order_by(TimeEntryORM.clock_in.desc()))
    items = res.scalars().all()
    return [_serialize_time_entry(e) for e in items]


@app.get("/api/time-entries/current")
async def get_current_time_entry(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    stmt = select(TimeEntryORM).where(TimeEntryORM.staff_id == current_user.id).where(TimeEntryORM.clock_out.is_(None))
    res = await db.execute(stmt.order_by(TimeEntryORM.clock_in.desc()))
    entry = res.scalars().first()

    all_rows = (
        await db.execute(
            select(TimeEntryORM)
            .where(TimeEntryORM.staff_id == current_user.id)
            .order_by(TimeEntryORM.clock_in.desc())
        )
    ).scalars().all()

    print("[DEBUG current-entry query]", {
        "current_user_id": current_user.id,
        "current_user_role": str(current_user.role),
        "active_entry_found": entry is not None,
        "active_entry_id": entry.id if entry else None,
        "all_entries_count": len(all_rows),
        "all_entries": [
            {
                "id": r.id,
                "staff_id": r.staff_id,
                "clock_in": r.clock_in.isoformat() if r.clock_in else None,
                "clock_out": r.clock_out.isoformat() if r.clock_out else None,
                "location_id": r.location_id,
            }
            for r in all_rows[:10]
        ],
    })

    return {
        "clocked_in": entry is not None,
        "entry": _serialize_time_entry(entry) if entry else None,
    }


@app.post("/api/time-entries/clock-in")
async def clock_in_time_entry(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    print("[DEBUG clock-in request]", {
        "payload": payload,
        "current_user_id": current_user.id,
        "current_user_role": str(current_user.role),
        "current_user_location_id": current_user.location_id,
    })
    staff_id = payload.get("staff_id") or current_user.id
    location_id = payload.get("location_id") or current_user.location_id

    if current_user.role == UserRole.STAFF and staff_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only clock in for yourself")

    if not location_id:
        first_location = (await db.execute(select(LocationORM).order_by(LocationORM.created_at.asc()))).scalars().first()
        if first_location:
            location_id = first_location.id

    if not location_id:
        raise HTTPException(status_code=400, detail="location_id is required")

    active = (
        await db.execute(
            select(TimeEntryORM)
            .where(TimeEntryORM.staff_id == staff_id)
            .where(TimeEntryORM.clock_out.is_(None))
            .order_by(TimeEntryORM.clock_in.desc())
        )
    ).scalars().first()

    if active:
        raise HTTPException(status_code=400, detail="Staff member is already clocked in")

    entry = TimeEntryORM(
        staff_id=staff_id,
        clock_in=datetime.now(timezone.utc),
        location_id=location_id,
        notes=payload.get("notes"),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    print("[DEBUG clock-in created]", {
        "id": entry.id,
        "staff_id": entry.staff_id,
        "clock_in": entry.clock_in.isoformat() if entry.clock_in else None,
        "clock_out": entry.clock_out.isoformat() if entry.clock_out else None,
        "location_id": entry.location_id,
    })
    return _serialize_time_entry(entry)


@app.post("/api/time-entries/clock-out")
async def clock_out_time_entry(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    print("[DEBUG clock-out request]", {
        "current_user_id": current_user.id,
        "current_user_role": str(current_user.role),
    })
    entry = (
        await db.execute(
            select(TimeEntryORM)
            .where(TimeEntryORM.staff_id == current_user.id)
            .where(TimeEntryORM.clock_out.is_(None))
            .order_by(TimeEntryORM.clock_in.desc())
        )
    ).scalars().first()

    if not entry:
        raise HTTPException(status_code=404, detail="No active time entry found")

    entry.clock_out = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(entry)
    print("[DEBUG clock-out completed]", {
        "id": entry.id,
        "staff_id": entry.staff_id,
        "clock_in": entry.clock_in.isoformat() if entry.clock_in else None,
        "clock_out": entry.clock_out.isoformat() if entry.clock_out else None,
    })
    return _serialize_time_entry(entry)



@app.get("/api/timeclock/entries")
async def get_timeclock_entries_alias(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return await get_time_entries(db=db, current_user=current_user)


@app.get("/api/timeclock/entries/current")
async def get_current_timeclock_entry_alias(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return await get_current_time_entry(db=db, current_user=current_user)


@app.post("/api/timeclock/clock-in")
async def clock_in_timeclock_alias(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return await clock_in_time_entry(payload=payload, db=db, current_user=current_user)


@app.post("/api/timeclock/clock-out")
async def clock_out_timeclock_alias(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    return await clock_out_time_entry(db=db, current_user=current_user)

@app.post("/api/time-entries")
async def create_time_entry(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    staff_id = payload.get("staff_id")
    clock_in = payload.get("clock_in")
    location_id = payload.get("location_id")
    notes = payload.get("notes")

    if not staff_id or not clock_in:
        raise HTTPException(status_code=400, detail="staff_id and clock_in are required")

    if not location_id:
        staff_user = (await db.execute(select(UserORM).where(UserORM.id == staff_id))).scalars().first()
        if staff_user and staff_user.location_id:
            location_id = staff_user.location_id
        else:
            first_location = (await db.execute(select(LocationORM).order_by(LocationORM.created_at.asc()))).scalars().first()
            if first_location:
                location_id = first_location.id

    if not location_id:
        raise HTTPException(status_code=400, detail="location_id is required")

    entry = TimeEntryORM(
        staff_id=staff_id,
        clock_in=datetime.fromisoformat(clock_in.replace("Z", "+00:00")),
        clock_out=datetime.fromisoformat(payload["clock_out"].replace("Z", "+00:00")) if payload.get("clock_out") else None,
        location_id=location_id,
        notes=notes,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return _serialize_time_entry(entry)


@app.patch("/api/time-entries/{entry_id}")
async def update_time_entry(
    entry_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    entry = (
        await db.execute(select(TimeEntryORM).where(TimeEntryORM.id == entry_id))
    ).scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")

    if "clock_in" in payload and payload["clock_in"]:
        entry.clock_in = datetime.fromisoformat(payload["clock_in"].replace("Z", "+00:00"))
    if "clock_out" in payload:
        entry.clock_out = datetime.fromisoformat(payload["clock_out"].replace("Z", "+00:00")) if payload["clock_out"] else None
    if "notes" in payload:
        entry.notes = payload["notes"]

    await db.commit()
    await db.refresh(entry)
    return _serialize_time_entry(entry)


@app.delete("/api/time-entries/{entry_id}")
async def delete_time_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    entry = (
        await db.execute(select(TimeEntryORM).where(TimeEntryORM.id == entry_id))
    ).scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")

    await db.delete(entry)
    await db.commit()
    return {"status": "deleted", "id": entry_id}


@app.get("/api/time-entries/modification-requests")
async def get_time_modification_requests(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    stmt = select(TimeModificationRequestORM)

    if current_user.role == UserRole.STAFF:
        stmt = stmt.where(TimeModificationRequestORM.staff_id == current_user.id)

    res = await db.execute(stmt.order_by(TimeModificationRequestORM.created_at.desc()))
    items = res.scalars().all()
    return [_serialize_time_mod_request(r) for r in items]


@app.post("/api/time-entries/modification-request")
async def create_time_modification_request(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    time_entry_id = payload.get("time_entry_id")
    requested_clock_in = payload.get("requested_clock_in")
    reason = payload.get("reason")

    if not time_entry_id or not requested_clock_in or not reason:
        raise HTTPException(status_code=400, detail="time_entry_id, requested_clock_in, and reason are required")

    entry = (
        await db.execute(select(TimeEntryORM).where(TimeEntryORM.id == time_entry_id))
    ).scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")

    if current_user.role == UserRole.STAFF and entry.staff_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only request changes for your own entries")

    existing = (
        await db.execute(
            select(TimeModificationRequestORM)
            .where(TimeModificationRequestORM.time_entry_id == time_entry_id)
            .where(TimeModificationRequestORM.status == TimeModificationStatus.PENDING)
            .order_by(TimeModificationRequestORM.created_at.desc())
        )
    ).scalars().first()

    if existing:
        raise HTTPException(status_code=409, detail="A pending modification request already exists for this entry")

    req = TimeModificationRequestORM(
        time_entry_id=time_entry_id,
        staff_id=entry.staff_id,
        staff_name=current_user.full_name,
        original_clock_in=entry.clock_in,
        original_clock_out=entry.clock_out,
        requested_clock_in=datetime.fromisoformat(requested_clock_in.replace("Z", "+00:00")),
        requested_clock_out=datetime.fromisoformat(payload["requested_clock_out"].replace("Z", "+00:00")) if payload.get("requested_clock_out") else None,
        reason=reason,
        status=TimeModificationStatus.PENDING,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return _serialize_time_mod_request(req)


@app.patch("/api/time-entries/modification-requests/{request_id}")
async def process_time_modification_request(
    request_id: str,
    action: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    req = (
        await db.execute(select(TimeModificationRequestORM).where(TimeModificationRequestORM.id == request_id))
    ).scalar_one_or_none()

    if not req:
        raise HTTPException(status_code=404, detail="Modification request not found")

    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action must be approve or reject")

    if action == "approve":
        req.status = TimeModificationStatus.APPROVED
        entry = (
            await db.execute(select(TimeEntryORM).where(TimeEntryORM.id == req.time_entry_id))
        ).scalar_one_or_none()
        if entry:
            entry.clock_in = req.requested_clock_in
            entry.clock_out = req.requested_clock_out
    else:
        req.status = TimeModificationStatus.REJECTED

    req.reviewed_by = current_user.id
    req.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(req)
    return _serialize_time_mod_request(req)


# ==================== TIME OFF COMPAT ROUTES ====================

def _serialize_time_off_request(a: AuditLogORM):
    details = a.details or {}
    return {
        "id": a.id,
        "staff_id": details.get("staff_id"),
        "staff_name": details.get("staff_name"),
        "leave_type": details.get("leave_type", "vacation"),
        "start_date": details.get("start_date"),
        "end_date": details.get("end_date"),
        "reason": details.get("reason"),
        "status": details.get("status", "pending"),
        "reviewed_by": details.get("reviewed_by"),
        "reviewed_at": details.get("reviewed_at"),
        "review_notes": details.get("review_notes"),
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }


@app.get("/api/time-off/requests")
async def get_time_off_requests(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    stmt = (
        select(AuditLogORM)
        .where(AuditLogORM.resource_type == "time_off_request")
        .order_by(AuditLogORM.created_at.desc())
    )
    res = await db.execute(stmt)
    items = res.scalars().all()
    return [_serialize_time_off_request(a) for a in items]


@app.get("/api/time-off/my-requests")
async def get_my_time_off_requests(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF)),
):
    stmt = (
        select(AuditLogORM)
        .where(AuditLogORM.resource_type == "time_off_request")
        .order_by(AuditLogORM.created_at.desc())
    )
    res = await db.execute(stmt)
    items = res.scalars().all()

    filtered = []
    for a in items:
        details = a.details or {}
        if details.get("staff_id") == current_user.id:
            filtered.append(a)

    return [_serialize_time_off_request(a) for a in filtered]


@app.get("/api/time-off/balances")
async def get_time_off_balances(
    current_user: UserORM = Depends(require_role(UserRole.STAFF)),
):
    return {}


@app.post("/api/time-off/requests")
async def create_time_off_request(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF)),
):
    leave_type = payload.get("leave_type", "vacation")
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    reason = payload.get("reason")

    if not start_date or not end_date:
        raise HTTPException(status_code=400, detail="start_date and end_date are required")

    audit = AuditLogORM(
        user_id=current_user.id,
        action=AuditAction.CREATE,
        resource_type="time_off_request",
        details={
            "staff_id": current_user.id,
            "staff_name": current_user.full_name,
            "leave_type": leave_type,
            "start_date": start_date,
            "end_date": end_date,
            "reason": reason,
            "status": "pending",
            "reviewed_by": None,
            "reviewed_at": None,
            "review_notes": None,
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)
    return _serialize_time_off_request(audit)


@app.post("/api/time-off/requests/{request_id}/approve")
async def approve_time_off_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    audit = (
        await db.execute(
            select(AuditLogORM).where(AuditLogORM.id == request_id)
        )
    ).scalar_one_or_none()

    if not audit or audit.resource_type != "time_off_request":
        raise HTTPException(status_code=404, detail="Time off request not found")

    details = dict(audit.details or {})
    details["status"] = "approved"
    details["reviewed_by"] = current_user.id
    details["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    audit.details = details

    await db.commit()
    await db.refresh(audit)
    return _serialize_time_off_request(audit)


@app.post("/api/time-off/requests/{request_id}/reject")
async def reject_time_off_request(
    request_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    audit = (
        await db.execute(
            select(AuditLogORM).where(AuditLogORM.id == request_id)
        )
    ).scalar_one_or_none()

    if not audit or audit.resource_type != "time_off_request":
        raise HTTPException(status_code=404, detail="Time off request not found")

    details = dict(audit.details or {})
    details["status"] = "rejected"
    details["reviewed_by"] = current_user.id
    details["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    details["review_notes"] = payload.get("reason")
    audit.details = details

    await db.commit()
    await db.refresh(audit)
    return _serialize_time_off_request(audit)


# ==================== ADMIN STAFF COMPAT ROUTE ====================

@app.get("/api/admin/staff")
async def get_admin_staff(
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(UserRole.STAFF, UserRole.ADMIN)),
):
    res = await db.execute(
        select(UserORM)
        .where(UserORM.role == UserRole.STAFF)
        .where(UserORM.is_active == True)
        .order_by(UserORM.full_name.asc())
    )
    items = res.scalars().all()

    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "phone": u.phone,
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "location_id": u.location_id,
            "is_active": u.is_active,
            "created_at": u.created_at,
        }
        for u in items
    ]