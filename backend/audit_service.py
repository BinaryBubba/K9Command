"""Small helper for writing audit log rows. Never raises: auditing must not break the action it records."""
from db_models import AuditLog as AuditLogORM, AuditAction


async def log_audit(db, user, action, resource_type, resource_id=None, description="", details=None):
    try:
        act = action if isinstance(action, AuditAction) else AuditAction(action)
        data = dict(details or {})
        if description:
            data["description"] = description
        db.add(AuditLogORM(
            organization_id=getattr(user, "organization_id", None),
            user_id=user.id,
            action=act,
            resource_type=resource_type,
            resource_id=resource_id,
            details=data,
        ))
        await db.commit()
    except Exception as e:
        try:
            await db.rollback()
        except Exception:
            pass
        print(f"audit log failed: {e}")
