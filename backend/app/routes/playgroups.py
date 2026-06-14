"""
Playgroups API
Automatic group suggestion algorithm + manual override with change tracking.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional, List
from datetime import datetime, timezone, date
from database import get_db
from auth import get_current_user
from db_models import User as UserORM
import uuid

router = APIRouter(prefix="/api/playgroups", tags=["playgroups"])

# Weight categories
def weight_category(weight):
    if not weight:
        return "unknown"
    w = float(weight)
    if w < 25:
        return "small"
    elif w < 55:
        return "medium"
    else:
        return "large"

def weight_compatible(w1, w2):
    """Returns penalty 0-100 for weight mismatch."""
    if not w1 or not w2:
        return 20  # unknown = small penalty
    diff = abs(float(w1) - float(w2))
    if diff <= 15:
        return 0
    elif diff <= 30:
        return 30
    elif diff <= 50:
        return 60
    return 100


async def get_onsite_dogs_with_profile(org_id: str, db: AsyncSession, target_date=None) -> list:
    """Get all dogs currently on site with full profile for grouping algorithm."""
    date_filter = target_date if target_date else date.today()
    result = await db.execute(text("""
        SELECT
            s.id as stay_id,
            s.dog_id,
            s.room_id,
            d.name as dog_name,
            d.weight,
            d.gender,
            d.spay_neuter_status,
            d.escape_risk,
            d.medical_alert,
            d.breed,
            d.age,
            d.behavioral_notes,
            d.other_notes,
            bp.bite_history,
            bp.food_guarding,
            bp.toy_guarding,
            bp.barrier_reactivity,
            bp.muzzle_required,
            bp.energy_level,
            bp.play_style,
            bp.anxiety_level,
            bp.handling_restrictions,
            bp.active_safety_alert,
            bp.safety_alert_detail,
            bp.prohibited_pairings,
            bp.approved_playgroups,
            bp.dog_compatibility,
            bp.is_humper,
            bp.is_wrestler,
            mag.outcome::text as mag_outcome,
            mag.notes as mag_notes
        FROM stays s
        JOIN dogs d ON s.dog_id = d.id
        LEFT JOIN behavior_profiles bp ON bp.dog_id = d.id
        LEFT JOIN (
            SELECT DISTINCT ON (dog_id) dog_id, outcome, notes
            FROM meet_and_greets
            WHERE outcome::text IS NOT NULL
            ORDER BY dog_id, scheduled_at DESC
        ) mag ON mag.dog_id = d.id
        WHERE s.organization_id = :org_id
        AND s.status::text IN ('CHECKED_IN', 'ON_SITE', 'on_site', 'checked_in')
        ORDER BY d.weight ASC NULLS LAST
    """), {"org_id": org_id})
    return [dict(r._mapping) for r in result.fetchall()]


def is_individual_only(dog: dict) -> tuple[bool, str]:
    """Returns (True, reason) if dog must be solo group."""
    if dog.get("bite_history"):
        return True, "Bite history"
    if dog.get("active_safety_alert"):
        return True, f"Safety alert: {dog.get('safety_alert_detail', 'active alert')}"
    if dog.get("muzzle_required"):
        return True, "Muzzle required"
    # Intact male
    sns = (dog.get("spay_neuter_status") or "").lower()
    gender = (dog.get("gender") or "").lower()
    if gender == "male" and sns in ["intact", "unneutered", "no", ""]:
        return True, "Intact male"
    # Anxiety/reactivity
    anxiety = dog.get("anxiety_level") or 0
    if anxiety and int(anxiety) >= 4:
        return True, "High anxiety/reactivity"
    # Humper or wrestler flags
    if dog.get("is_humper"):
        return True, "Humper — individual group"
    if dog.get("is_wrestler"):
        return True, "Wrestler — individual group"
    # Anxiety/reactivity from level field
    anxiety = dog.get("anxiety_level")
    if anxiety and int(anxiety) >= 4:
        return True, "High anxiety/reactivity"
    # Check behavioral notes for keywords
    notes = ((dog.get("behavioral_notes") or "") + " " + (dog.get("other_notes") or "") + " " + (dog.get("handling_restrictions") or "")).lower()
    if any(k in notes for k in ["individual", "solo", "reactive", "anxious", "aggressive"]):
        return True, "Individual (behavioral notes)"
    return False, ""


def score_pair(d1: dict, d2: dict, history: list) -> int:
    """Lower score = more compatible. Returns penalty score."""
    penalty = 0

    # Hard block: prohibited pairings from behavior profile
    import json as _json
    prohibited = d1.get("prohibited_pairings")
    if prohibited:
        if isinstance(prohibited, str):
            try: prohibited = _json.loads(prohibited)
            except: prohibited = []
        for pair in (prohibited or []):
            if str(pair).lower() in (d2.get("dog_name") or "").lower():
                penalty += 1000

    # Hard block: avoid pairs from M&G notes
    mag_notes = (d1.get("mag_notes") or "").lower()
    if d2.get("dog_name", "").lower() in mag_notes and "avoid" in mag_notes:
        penalty += 1000

    # Compatibility field
    compat = (d1.get("dog_compatibility") or "").lower()
    if "not" in compat or "no" in compat:
        penalty += 500

    # Weight compatibility
    penalty += weight_compatible(d1.get("weight"), d2.get("weight"))

    # Energy level mismatch
    e1 = d1.get("energy_level") or 3
    e2 = d2.get("energy_level") or 3
    energy_diff = abs(int(e1) - int(e2))
    penalty += energy_diff * 15

    # Past positive interaction bonus
    d1_name = (d1.get("dog_name") or "").lower()
    d2_name = (d2.get("dog_name") or "").lower()
    for h in history:
        if h.get("dog1") == d1_name and h.get("dog2") == d2_name:
            penalty -= 20  # bonus for known good pair
        if h.get("dog1") == d2_name and h.get("dog2") == d1_name:
            penalty -= 20

    return max(0, penalty)


def suggest_groups(dogs: list, history: list) -> list:
    """
    Returns list of groups: [{"group_number": 1, "is_individual": False, "dogs": [...], "reason": ""}]
    """
    groups = []
    group_num = 1
    unassigned = list(dogs)

    # First pass: pull out individual-only dogs
    for dog in list(unassigned):
        is_solo, reason = is_individual_only(dog)
        if is_solo:
            groups.append({
                "group_number": group_num,
                "is_individual": True,
                "reason": reason,
                "dogs": [dog],
            })
            group_num += 1
            unassigned.remove(dog)

    # Second pass: greedy grouping by compatibility
    while unassigned:
        # Start new group with first unassigned dog
        seed = unassigned.pop(0)
        group_dogs = [seed]
        max_group_size = 6

        for dog in list(unassigned):
            if len(group_dogs) >= max_group_size:
                break
            # Check compatibility with all dogs in current group
            total_penalty = sum(score_pair(dog, g, history) for g in group_dogs)
            avg_penalty = total_penalty / len(group_dogs)
            if avg_penalty < 60:  # threshold for compatibility
                group_dogs.append(dog)
                unassigned.remove(dog)

        groups.append({
            "group_number": group_num,
            "is_individual": len(group_dogs) == 1,
            "reason": "Auto-grouped" if len(group_dogs) > 1 else "Solo — no compatible partners",
            "dogs": group_dogs,
        })
        group_num += 1

    return groups


@router.get("/today")
async def get_today_groups(
    target_date: Optional[str] = Query(None),
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    today = date.fromisoformat(target_date) if target_date else date.today()

    result = await db.execute(text("""
        SELECT pg.id, pg.group_number, pg.label, pg.is_individual, pg.notes,
               pm.id as member_id, pm.stay_id, pm.dog_id, pm.assigned_at, pm.notes as member_notes,
               d.name as dog_name, d.weight, d.breed, d.gender,
               r.name as room_name
        FROM playgroups pg
        JOIN playgroup_members pm ON pm.playgroup_id = pg.id AND pm.removed_at IS NULL
        JOIN dogs d ON pm.dog_id = d.id
        LEFT JOIN stays s ON pm.stay_id = s.id
        LEFT JOIN rooms r ON s.room_id = r.id
        WHERE pg.organization_id = :org_id AND pg.group_date = :today
        ORDER BY pg.group_number, d.name
    """), {"org_id": org_id, "today": today})

    rows = result.fetchall()

    # Build group dict
    groups = {}
    for row in rows:
        gid = row.id
        if gid not in groups:
            groups[gid] = {
                "id": gid,
                "group_number": row.group_number,
                "label": row.label,
                "is_individual": row.is_individual,
                "notes": row.notes,
                "dogs": [],
            }
        groups[gid]["dogs"].append({
            "member_id": row.member_id,
            "stay_id": row.stay_id,
            "dog_id": row.dog_id,
            "dog_name": row.dog_name,
            "weight": float(row.weight) if row.weight else None,
            "breed": row.breed,
            "gender": row.gender,
            "room_name": row.room_name,
            "member_notes": row.member_notes,
            "assigned_at": row.assigned_at.isoformat() if row.assigned_at else None,
        })

    return list(groups.values())


@router.post("/suggest")
async def suggest_groups_endpoint(
    data: dict = {},
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = current_user.organization_id
    raw_date2 = data.get("date") or date.today().isoformat()
    target_date = date.fromisoformat(raw_date2) if isinstance(raw_date2, str) else raw_date2

    dogs = await get_onsite_dogs_with_profile(org_id, db, target_date)
    if not dogs:
        return {"groups": [], "message": "No dogs currently on site"}

    # Load history of successful past groupings
    history_result = await db.execute(text("""
        SELECT d1.name as dog1, d2.name as dog2
        FROM playgroup_members pm1
        JOIN playgroup_members pm2 ON pm1.playgroup_id = pm2.playgroup_id
            AND pm1.dog_id != pm2.dog_id
            AND pm1.removed_at IS NULL AND pm2.removed_at IS NULL
        JOIN dogs d1 ON pm1.dog_id = d1.id
        JOIN dogs d2 ON pm2.dog_id = d2.id
        JOIN playgroups pg ON pm1.playgroup_id = pg.id
        WHERE pg.organization_id = :org_id
        AND pg.is_individual = FALSE
        LIMIT 500
    """), {"org_id": org_id})
    history = [{"dog1": r.dog1.lower(), "dog2": r.dog2.lower()} for r in history_result.fetchall()]

    suggested = suggest_groups(dogs, history)
    return {"groups": suggested, "date": str(target_date), "total_dogs": len(dogs)}


@router.post("/assign")
async def assign_groups(
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save suggested or manually arranged groups for today."""
    org_id = current_user.organization_id
    raw_date = data.get("date") or date.today().isoformat()
    target_date = date.fromisoformat(raw_date) if isinstance(raw_date, str) else raw_date
    groups = data.get("groups", [])

    # Delete existing groups for today
    await db.execute(text("""
        DELETE FROM playgroup_members WHERE playgroup_id IN (
            SELECT id FROM playgroups WHERE organization_id = :org_id AND group_date = :date
        )
    """), {"org_id": org_id, "date": target_date})
    await db.execute(text("""
        DELETE FROM playgroups WHERE organization_id = :org_id AND group_date = :date
    """), {"org_id": org_id, "date": target_date})

    created_groups = []
    for g in groups:
        pg_id = str(uuid.uuid4())
        await db.execute(text("""
            INSERT INTO playgroups (id, organization_id, group_date, group_number, label, is_individual, notes, created_by)
            VALUES (:id, :org_id, :date, :num, :label, :individual, :notes, :created_by)
        """), {
            "id": pg_id,
            "org_id": org_id,
            "date": target_date,
            "num": g.get("group_number", 0),
            "label": g.get("label") or f"Group {g.get('group_number', 0)}",
            "individual": g.get("is_individual", False),
            "notes": g.get("reason") or g.get("notes"),
            "created_by": current_user.id,
        })

        for dog in g.get("dogs", []):
            await db.execute(text("""
                INSERT INTO playgroup_members (id, organization_id, playgroup_id, stay_id, dog_id, assigned_by, notes)
                VALUES (:id, :org_id, :pg_id, :stay_id, :dog_id, :assigned_by, :notes)
            """), {
                "id": str(uuid.uuid4()),
                "org_id": org_id,
                "pg_id": pg_id,
                "stay_id": dog.get("stay_id"),
                "dog_id": dog.get("dog_id"),
                "assigned_by": current_user.id,
                "notes": dog.get("member_notes"),
            })
        created_groups.append(pg_id)

    await db.commit()
    return {"saved": len(created_groups), "date": str(target_date)}


@router.patch("/{playgroup_id}/move")
async def move_dog(
    playgroup_id: str,
    data: dict,
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Move a dog from one group to another, with change tracking."""
    org_id = current_user.organization_id
    dog_id = data.get("dog_id")
    to_group_id = data.get("to_group_id")
    reason = data.get("reason", "")
    stay_id = data.get("stay_id")

    if not dog_id or not to_group_id:
        raise HTTPException(status_code=400, detail="dog_id and to_group_id required")

    # Remove from current group
    await db.execute(text("""
        UPDATE playgroup_members SET removed_at = NOW(), removed_by = :user_id
        WHERE playgroup_id = :pg_id AND dog_id = :dog_id AND removed_at IS NULL
    """), {"pg_id": playgroup_id, "dog_id": dog_id, "user_id": current_user.id})

    # Add to new group
    await db.execute(text("""
        INSERT INTO playgroup_members (id, organization_id, playgroup_id, stay_id, dog_id, assigned_by)
        VALUES (:id, :org_id, :pg_id, :stay_id, :dog_id, :user_id)
    """), {
        "id": str(uuid.uuid4()),
        "org_id": org_id,
        "pg_id": to_group_id,
        "stay_id": stay_id,
        "dog_id": dog_id,
        "user_id": current_user.id,
    })

    # Log the change
    await db.execute(text("""
        INSERT INTO playgroup_changes (id, organization_id, dog_id, stay_id, from_group_id, to_group_id, changed_by, reason)
        VALUES (:id, :org_id, :dog_id, :stay_id, :from_id, :to_id, :user_id, :reason)
    """), {
        "id": str(uuid.uuid4()),
        "org_id": org_id,
        "dog_id": dog_id,
        "stay_id": stay_id,
        "from_id": playgroup_id,
        "to_id": to_group_id,
        "user_id": current_user.id,
        "reason": reason,
    })

    await db.commit()
    return {"moved": True, "dog_id": dog_id, "to_group_id": to_group_id}


@router.get("/history")
async def get_group_history(
    dog_id: Optional[str] = Query(None),
    limit: int = Query(50),
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get history of group changes for learning and audit."""
    org_id = current_user.organization_id
    conditions = ["pc.organization_id = :org_id"]
    params = {"org_id": org_id, "limit": limit}
    if dog_id:
        conditions.append("pc.dog_id = :dog_id")
        params["dog_id"] = dog_id

    where = " AND ".join(conditions)
    result = await db.execute(text(f"""
        SELECT pc.id, pc.changed_at, pc.reason,
               d.name as dog_name,
               u.full_name as changed_by_name,
               pg_from.group_number as from_group,
               pg_to.group_number as to_group
        FROM playgroup_changes pc
        JOIN dogs d ON pc.dog_id = d.id
        LEFT JOIN users u ON pc.changed_by = u.id
        LEFT JOIN playgroups pg_from ON pc.from_group_id = pg_from.id
        LEFT JOIN playgroups pg_to ON pc.to_group_id = pg_to.id
        WHERE {where}
        ORDER BY pc.changed_at DESC
        LIMIT :limit
    """), params)

    return [dict(r._mapping) for r in result.fetchall()]


@router.get("/unassigned")
async def get_unassigned_dogs(
    current_user: UserORM = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get dogs on site that haven't been assigned to a group today."""
    org_id = current_user.organization_id
    today = date.today()

    result = await db.execute(text("""
        SELECT s.id as stay_id, s.dog_id, d.name as dog_name, d.weight, d.breed, r.name as room_name
        FROM stays s
        JOIN dogs d ON s.dog_id = d.id
        LEFT JOIN rooms r ON s.room_id = r.id
        WHERE s.organization_id = :org_id
        AND s.status::text IN ('CHECKED_IN', 'ON_SITE', 'on_site', 'checked_in')
        AND s.dog_id NOT IN (
            SELECT pm.dog_id FROM playgroup_members pm
            JOIN playgroups pg ON pm.playgroup_id = pg.id
            WHERE pg.organization_id = :org_id
            AND pg.group_date = :today
            AND pm.removed_at IS NULL
        )
    """), {"org_id": org_id, "today": today})

    return [dict(r._mapping) for r in result.fetchall()]
