"""
MinIO storage service for K9CMD.
Uses the official minio-py client.
"""
import os
import uuid
import io
from typing import Optional
from minio import Minio
from minio.error import S3Error

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "k9cmd_minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "K9cmd_MinIO_2024!")
MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "false").lower() == "true"

BUCKET_DOGS = os.getenv("MINIO_BUCKET_DOGS", "dog-files")
BUCKET_VACCINATIONS = os.getenv("MINIO_BUCKET_VACCINATIONS", "vaccination-records")
BUCKET_INCIDENTS = os.getenv("MINIO_BUCKET_INCIDENTS", "incident-photos")
BUCKET_MAG = "mag-photos"

def get_client() -> Minio:
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_USE_SSL,
    )

def upload_file(bucket: str, file_data: bytes, filename: str, content_type: str = "application/octet-stream") -> str:
    """Upload a file and return the object key."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    key = f"{uuid.uuid4()}.{ext}"
    client = get_client()
    client.put_object(
        bucket, key,
        data=io.BytesIO(file_data),
        length=len(file_data),
        content_type=content_type,
    )
    return key

def get_presigned_url(bucket: str, key: str, expires_in: int = 3600) -> Optional[str]:
    """Generate a presigned URL for temporary access."""
    if not key:
        return None
    try:
        from datetime import timedelta
        client = get_client()
        internal_url = client.presigned_get_object(bucket, key, expires=timedelta(seconds=expires_in))
        # Replace internal minio:9000 with public URL via Caddy proxy
        public_base = os.getenv("MINIO_PUBLIC_URL", "")
        if public_base and internal_url:
            import re
            # Replace http://minio:9000/bucket/key with public_base/bucket/key
            internal_url = re.sub(r"http://minio:9000", public_base, internal_url)
        return internal_url
    except Exception:
        return None

def delete_file(bucket: str, key: str) -> bool:
    """Delete a file from storage."""
    try:
        client = get_client()
        client.remove_object(bucket, key)
        return True
    except Exception:
        return False
