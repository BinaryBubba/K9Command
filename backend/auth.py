"""
Authentication utilities using PostgreSQL (SQLAlchemy)
"""
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Security, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os

from database import get_db
from db_models import User as UserORM, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_DAYS = int(os.environ.get("JWT_EXPIRATION_DAYS", "30"))

if JWT_SECRET == "dev-secret-change-in-production":
    print("⚠ WARNING: Using default JWT_SECRET. Set JWT_SECRET env var for production!")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRATION_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid authentication credentials: {e}")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
    x_dev_secret: str | None = Header(default=None, alias="X-Dev-Secret"),
):
    # DEV BYPASS
    if x_dev_secret == os.getenv("DEV_ADMIN_SECRET"):
        result = await db.execute(
            select(UserORM).where(UserORM.role == UserRole.ADMIN).limit(1)
        )
        user = result.scalar_one_or_none()
        if user:
            return user
        raise HTTPException(status_code=500, detail="Dev bypass requested but no admin user exists")

    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token - missing user ID")

    result = await db.execute(select(UserORM).where(UserORM.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user



def require_role(*allowed_roles: UserRole):
    async def role_checker(
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
        db: AsyncSession = Depends(get_db),
        x_dev_secret: str | None = Header(default=None, alias="X-Dev-Secret"),
    ):
        user = await get_current_user(
            credentials=credentials,
            db=db,
            x_dev_secret=x_dev_secret,
        )
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker


async def get_current_org(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns (user, organization) for the current request.
    Raises 403 if the user has no organization assigned.
    """
    from db_models import Organization
    if not current_user.organization_id:
        raise HTTPException(status_code=403, detail="User has no organization assigned")
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=403, detail="Organization not found")
    return current_user, org
