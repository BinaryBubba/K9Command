"""
Background cron worker — runs daily at midnight.
Handles recurring task creation.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta, date
from sqlalchemy import text
from database import AsyncSessionLocal
import uuid

logger = logging.getLogger(__name__)

RECURRENCE_DELTAS = {
    "daily": timedelta(days=1),
    "weekdays": timedelta(days=1),  # handled specially
    "weekly": timedelta(weeks=1),
    "biweekly": timedelta(weeks=2),
    "monthly": timedelta(days=30),
}


async def create_recurring_tasks():
    """Find completed recurring tasks and create next occurrence."""
    async with AsyncSessionLocal() as db:
        try:
            # Find recently completed recurring tasks that don't have a future copy
            result = await db.execute(text("""
                SELECT t.id, t.organization_id, t.title, t.description,
                       t.assigned_to, t.location_id, t.priority, t.recurrence,
                       t.due_date, t.checklist, t.tags, t.dog_id, t.stay_id,
                       t.completed_at
                FROM tasks t
                WHERE t.recurrence IS NOT NULL
                AND t.recurrence != ''
                AND t.status::text = 'COMPLETED'
                AND t.completed_at >= NOW() - INTERVAL '25 hours'
                AND NOT EXISTS (
                    SELECT 1 FROM tasks t2
                    WHERE t2.organization_id = t.organization_id
                    AND t2.title = t.title
                    AND t2.recurrence = t.recurrence
                    AND t2.status::text NOT IN ('COMPLETED', 'CANCELLED')
                    AND t2.id != t.id
                )
            """))
            tasks = result.fetchall()
            logger.info(f"Cron: found {len(tasks)} recurring tasks to renew")

            for task in tasks:
                recurrence = task.recurrence
                delta = RECURRENCE_DELTAS.get(recurrence, timedelta(days=1))
                base_date = task.due_date or datetime.now(timezone.utc)

                # Calculate next due date
                next_due = base_date + delta

                # For weekdays, skip weekend
                if recurrence == "weekdays":
                    while next_due.weekday() >= 5:  # 5=Sat, 6=Sun
                        next_due += timedelta(days=1)

                new_id = str(uuid.uuid4())
                await db.execute(text("""
                    INSERT INTO tasks (
                        id, organization_id, title, description, assigned_to,
                        location_id, priority, status, recurrence, due_date,
                        checklist, tags, dog_id, stay_id, created_by, created_at, updated_at
                    ) VALUES (
                        :id, :org_id, :title, :description, :assigned_to,
                        :location_id, :priority, 'PENDING', :recurrence, :due_date,
                        :checklist, :tags, :dog_id, :stay_id, :assigned_to, NOW(), NOW()
                    )
                """), {
                    "id": new_id,
                    "org_id": task.organization_id,
                    "title": task.title,
                    "description": task.description,
                    "assigned_to": task.assigned_to,
                    "location_id": task.location_id,
                    "priority": task.priority or "MEDIUM",
                    "recurrence": recurrence,
                    "due_date": next_due,
                    "checklist": task.checklist,
                    "tags": task.tags,
                    "dog_id": task.dog_id,
                    "stay_id": task.stay_id,
                })
                logger.info(f"Cron: created recurring task '{task.title}' due {next_due.date()}")

            await db.commit()
            logger.info(f"Cron: recurring tasks complete, created {len(tasks)} new tasks")

        except Exception as e:
            logger.error(f"Cron error: {e}")
            await db.rollback()


async def run_cron_loop():
    """Run cron tasks daily at midnight."""
    logger.info("Cron worker started")
    while True:
        now = datetime.now(timezone.utc)
        # Calculate seconds until next midnight UTC
        tomorrow = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        wait_seconds = (tomorrow - now).total_seconds()
        logger.info(f"Cron: next run in {wait_seconds/3600:.1f} hours")
        await asyncio.sleep(wait_seconds)
        await create_recurring_tasks()
