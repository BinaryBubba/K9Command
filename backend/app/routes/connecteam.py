"""
Connecteam Integration
Syncs shift/clock data from Connecteam API to K9CMD
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db
from auth import get_current_user, require_role
from db_models import User as UserORM, UserRole
import httpx
import os

router = APIRouter(prefix="/api/connecteam", tags=["connecteam"])

CONNECTEAM_API_KEY = os.getenv("CONNECTEAM_API_KEY", "")
CONNECTEAM_COMPANY_ID = os.getenv("CONNECTEAM_COMPANY_ID", "")
CONNECTEAM_BASE = "https://api.connecteam.com/v1"


async def ct_get(endpoint: str) -> dict:
    """Make authenticated request to Connecteam API."""
    if not CONNECTEAM_API_KEY:
        raise HTTPException(status_code=503, detail="Connecteam API key not configured")
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{CONNECTEAM_BASE}{endpoint}",
            headers={
                "Authorization": f"Bearer {CONNECTEAM_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail=f"Connecteam API error: {res.text}")
        return res.json()


@router.get("/status")
async def connecteam_status(
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    """Check if Connecteam integration is configured."""
    return {
        "configured": bool(CONNECTEAM_API_KEY),
        "company_id": CONNECTEAM_COMPANY_ID or None,
        "api_key_set": bool(CONNECTEAM_API_KEY),
    }


@router.get("/shifts/active")
async def get_active_shifts(
    current_user: UserORM = Depends(require_role(UserRole.ADMIN, UserRole.STAFF, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """
    Get currently active shifts from Connecteam and map to K9CMD staff.
    Returns combined data showing who is clocked in.
    """
    if not CONNECTEAM_API_KEY:
        return {"source": "k9cmd_only", "shifts": [], "message": "Connecteam not configured"}

    try:
        # Fetch active clock entries from Connecteam
        ct_data = await ct_get(f"/companies/{CONNECTEAM_COMPANY_ID}/timeclock/active")
        ct_shifts = ct_data.get("data", [])

        # Map Connecteam users to K9CMD users via connecteam_user_id
        result = await db.execute(text("""
            SELECT id, full_name, role, connecteam_user_id, shift_started_at
            FROM users
            WHERE organization_id = :org_id
            AND connecteam_user_id IS NOT NULL
        """), {"org_id": current_user.organization_id})
        k9_users = {r.connecteam_user_id: r for r in result.fetchall()}

        shifts = []
        for shift in ct_shifts:
            ct_user_id = str(shift.get("userId", ""))
            k9_user = k9_users.get(ct_user_id)
            shifts.append({
                "connecteam_user_id": ct_user_id,
                "connecteam_name": shift.get("userName"),
                "clocked_in_at": shift.get("startTime"),
                "k9cmd_user_id": k9_user.id if k9_user else None,
                "k9cmd_name": k9_user.full_name if k9_user else None,
                "k9cmd_role": k9_user.role if k9_user else None,
                "mapped": k9_user is not None,
            })

        return {"source": "connecteam", "shifts": shifts, "total": len(shifts)}

    except HTTPException:
        raise
    except Exception as e:
        return {"source": "error", "shifts": [], "error": str(e)}


@router.post("/webhook")
async def connecteam_webhook(
    payload: dict,
    x_connecteam_signature: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Receive clock in/out webhooks from Connecteam.
    Configure in Connecteam: Settings -> Integrations -> Webhooks
    URL: https://k9cmd.maniacranch.com/api/connecteam/webhook

    SECURITY NOTE: x_connecteam_signature is accepted but NOT verified.
    This endpoint is unauthenticated by necessity (webhooks can't send a
    bearer token), so it MUST verify a signature before trusting payload
    contents once this integration is actually turned on -- otherwise
    anyone who learns/guesses a staff connecteam_user_id can toggle their
    shift status. Consult Connecteam's webhook docs for their exact HMAC
    scheme and implement verification here before setting
    CONNECTEAM_API_KEY in production. Until then, this handler no-ops
    unless the integration is explicitly configured, closing the gap
    where it could be hit while dormant.
    """
    if not CONNECTEAM_API_KEY:
        return {"received": False, "reason": "Connecteam integration not configured"}

    event_type = payload.get("eventType", "")
    user_id = str(payload.get("userId", ""))
    timestamp = payload.get("timestamp")

    if not user_id:
        return {"received": True}

    # Find K9CMD user by Connecteam ID
    result = await db.execute(text("""
        SELECT id FROM users WHERE connecteam_user_id = :ct_id LIMIT 1
    """), {"ct_id": user_id})
    row = result.fetchone()
    if not row:
        return {"received": True, "mapped": False}

    k9_user_id = row[0]

    if event_type in ["clockIn", "clock_in", "CLOCK_IN"]:
        await db.execute(text("""
            UPDATE users SET is_on_shift = TRUE, shift_started_at = NOW()
            WHERE id = :user_id
        """), {"user_id": k9_user_id})
    elif event_type in ["clockOut", "clock_out", "CLOCK_OUT"]:
        await db.execute(text("""
            UPDATE users SET is_on_shift = FALSE, shift_started_at = NULL
            WHERE id = :user_id
        """), {"user_id": k9_user_id})

    await db.commit()
    return {"received": True, "mapped": True, "event": event_type}


@router.post("/sync")
async def sync_connecteam_shifts(
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Manual sync - pull current Connecteam shifts and update K9CMD shift status.
    """
    if not CONNECTEAM_API_KEY:
        raise HTTPException(status_code=503, detail="Connecteam not configured")

    try:
        ct_data = await ct_get(f"/companies/{CONNECTEAM_COMPANY_ID}/timeclock/active")
        active_ct_ids = {str(s.get("userId")) for s in ct_data.get("data", [])}

        # Update all mapped users
        result = await db.execute(text("""
            SELECT id, connecteam_user_id FROM users
            WHERE organization_id = :org_id AND connecteam_user_id IS NOT NULL
        """), {"org_id": current_user.organization_id})
        
        updated = 0
        for row in result.fetchall():
            is_active = row.connecteam_user_id in active_ct_ids
            await db.execute(text("""
                UPDATE users SET is_on_shift = :active,
                shift_started_at = CASE WHEN :active THEN COALESCE(shift_started_at, NOW()) ELSE NULL END
                WHERE id = :user_id
            """), {"active": is_active, "user_id": row.id})
            updated += 1

        await db.commit()
        return {"synced": updated, "active_ct_shifts": len(active_ct_ids)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/users/{user_id}/link")
async def link_connecteam_user(
    user_id: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Link a K9CMD staff member to their Connecteam user ID."""
    ct_id = data.get("connecteam_user_id", "").strip()
    await db.execute(text("""
        UPDATE users SET connecteam_user_id = :ct_id
        WHERE id = :user_id AND organization_id = :org_id
    """), {"ct_id": ct_id or None, "user_id": user_id, "org_id": current_user.organization_id})
    await db.commit()
    return {"linked": True, "connecteam_user_id": ct_id}
