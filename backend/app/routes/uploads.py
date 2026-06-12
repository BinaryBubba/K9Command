"""
File upload API - handles vaccination PDFs, dog photos, incident images.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from auth import get_current_user
from db_models import User as UserORM
from app.storage import upload_file, get_presigned_url, BUCKET_VACCINATIONS, BUCKET_DOGS, BUCKET_INCIDENTS, BUCKET_MAG
import uuid

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_DOC_TYPES = {"application/pdf"} | ALLOWED_IMAGE_TYPES
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/vaccination")
async def upload_vaccination(
    file: UploadFile = File(...),
    current_user: UserORM = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF and image files allowed")
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    key = upload_file(BUCKET_VACCINATIONS, data, file.filename or "upload", file.content_type)
    url = get_presigned_url(BUCKET_VACCINATIONS, key, expires_in=86400)
    return {"key": key, "url": url, "filename": file.filename, "content_type": file.content_type}


@router.post("/dog-photo")
async def upload_dog_photo(
    file: UploadFile = File(...),
    current_user: UserORM = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only image files allowed")
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    key = upload_file(BUCKET_DOGS, data, file.filename or "photo", file.content_type)
    url = get_presigned_url(BUCKET_DOGS, key, expires_in=86400)
    return {"key": key, "url": url}


@router.post("/incident")
async def upload_incident_photo(
    file: UploadFile = File(...),
    current_user: UserORM = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only image files allowed")
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    key = upload_file(BUCKET_INCIDENTS, data, file.filename or "photo", file.content_type)
    url = get_presigned_url(BUCKET_INCIDENTS, key, expires_in=86400)
    return {"key": key, "url": url}


@router.post("/mag-photo")
async def upload_mag_photo(
    file: UploadFile = File(...),
    current_user: UserORM = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only image files allowed")
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    key = upload_file(BUCKET_MAG, data, file.filename or "photo", file.content_type)
    url = get_presigned_url(BUCKET_MAG, key, expires_in=86400)
    return {"key": key, "url": url}


@router.get("/url")
async def get_file_url(
    bucket: str,
    key: str,
    current_user: UserORM = Depends(get_current_user),
):
    """Get a fresh presigned URL for a stored file."""
    url = get_presigned_url(bucket, key, expires_in=3600)
    if not url:
        raise HTTPException(status_code=404, detail="File not found")
    return {"url": url}

@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: UserORM = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only image files allowed")
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    key = upload_file(BUCKET_DOGS, data, file.filename or "avatar", file.content_type)
    url = get_presigned_url(BUCKET_DOGS, key, expires_in=86400)
    return {"key": key, "url": url}
