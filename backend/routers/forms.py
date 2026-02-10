"""
Forms Engine Router - Connecteam Parity
Handles form templates, submissions, signatures, attachments
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid
import base64

from models import (
    UserRole,
    FormTemplate, FormTemplateCreate, FormTemplateResponse, FormField, FormFieldType,
    FormSubmission, FormSubmissionCreate, FormSubmissionResponse, FormSubmissionStatus,
    TaskTemplate, TaskTemplateCreate, TaskTemplateResponse,
    EnhancedTask, TaskStatus,
)
from auth import get_current_user

router = APIRouter(prefix="/api/forms", tags=["Forms"])
security = HTTPBearer()


def get_db():
    """Get database connection - will be injected"""
    from server import db
    return db


# ==================== FORM TEMPLATES ====================

@router.get("/templates", response_model=List[FormTemplateResponse])
async def list_form_templates(
    category: Optional[str] = None,
    is_active: bool = True,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List form templates"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    query = {"is_active": is_active}
    if category:
        query["category"] = category
    
    # Filter by assignable_to for non-admins
    if user.role != UserRole.ADMIN:
        query["$or"] = [
            {"assignable_to": "all"},
            {"assignable_to": user.role.value},
            {"assignable_to": f"role:{user.role.value}"}
        ]
    
    templates = await db.form_templates.find(query, {"_id": 0}).to_list(100)
    return [FormTemplateResponse(**t) for t in templates]


@router.get("/templates/{template_id}", response_model=FormTemplateResponse)
async def get_form_template(
    template_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a single form template"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    template = await db.form_templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Form template not found")
    
    return FormTemplateResponse(**template)


@router.post("/templates", response_model=FormTemplateResponse)
async def create_form_template(
    data: FormTemplateCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a form template (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Convert field dicts to FormField objects and back to ensure validation
    fields = []
    for i, field_data in enumerate(data.fields):
        field = FormField(
            id=field_data.get('id', str(uuid.uuid4())),
            field_type=FormFieldType(field_data.get('field_type', 'text')),
            label=field_data.get('label', ''),
            placeholder=field_data.get('placeholder'),
            help_text=field_data.get('help_text'),
            required=field_data.get('required', False),
            min_length=field_data.get('min_length'),
            max_length=field_data.get('max_length'),
            min_value=field_data.get('min_value'),
            max_value=field_data.get('max_value'),
            pattern=field_data.get('pattern'),
            options=field_data.get('options', []),
            show_if=field_data.get('show_if'),
            order=field_data.get('order', i),
            width=field_data.get('width', 'full')
        )
        fields.append(field.model_dump())
    
    template = FormTemplate(
        name=data.name,
        description=data.description,
        location_id=data.location_id,
        fields=fields,
        assignable_to=data.assignable_to,
        require_signature=data.require_signature,
        require_gps=data.require_gps,
        allow_save_draft=data.allow_save_draft,
        allow_edit_after_submit=data.allow_edit_after_submit,
        notify_on_submit=data.notify_on_submit,
        is_active=data.is_active,
        category=data.category,
        tags=data.tags
    )
    
    doc = template.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.form_templates.insert_one(doc)
    return FormTemplateResponse(**template.model_dump())


@router.patch("/templates/{template_id}", response_model=FormTemplateResponse)
async def update_form_template(
    template_id: str,
    updates: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update a form template (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    existing = await db.form_templates.find_one({"id": template_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Form template not found")
    
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    updates['version'] = existing.get('version', 1) + 1
    
    await db.form_templates.update_one(
        {"id": template_id},
        {"$set": updates}
    )
    
    template = await db.form_templates.find_one({"id": template_id}, {"_id": 0})
    return FormTemplateResponse(**template)


@router.delete("/templates/{template_id}")
async def delete_form_template(
    template_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete (deactivate) a form template (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.form_templates.update_one(
        {"id": template_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Form template not found")
    
    return {"message": "Form template deactivated"}


# ==================== FORM SUBMISSIONS ====================

@router.get("/submissions", response_model=List[FormSubmissionResponse])
async def list_form_submissions(
    template_id: Optional[str] = None,
    status: Optional[str] = None,
    submitted_by: Optional[str] = None,
    related_type: Optional[str] = None,
    related_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List form submissions"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    query = {}
    
    # Staff can only see their own submissions unless admin
    if user.role == UserRole.STAFF:
        query["submitted_by"] = user.id
    elif submitted_by:
        query["submitted_by"] = submitted_by
    
    if template_id:
        query["template_id"] = template_id
    if status:
        query["status"] = status
    if related_type:
        query["related_type"] = related_type
    if related_id:
        query["related_id"] = related_id
    
    submissions = await db.form_submissions.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [FormSubmissionResponse(**s) for s in submissions]


@router.get("/submissions/{submission_id}", response_model=FormSubmissionResponse)
async def get_form_submission(
    submission_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a single form submission"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    submission = await db.form_submissions.find_one({"id": submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Form submission not found")
    
    # Check access
    if user.role == UserRole.STAFF and submission['submitted_by'] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return FormSubmissionResponse(**submission)


@router.post("/submissions", response_model=FormSubmissionResponse)
async def create_form_submission(
    data: FormSubmissionCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a form submission"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    # Get template
    template = await db.form_templates.find_one({"id": data.template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Form template not found")
    
    # Validate required fields if submitting (not draft)
    if data.status == FormSubmissionStatus.SUBMITTED:
        for field in template.get('fields', []):
            if field.get('required') and field['id'] not in data.values:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Required field missing: {field.get('label', field['id'])}"
                )
        
        # Check signature requirement
        if template.get('require_signature') and not data.signature_data:
            raise HTTPException(status_code=400, detail="Signature required")
        
        # Check GPS requirement
        if template.get('require_gps') and not data.gps_latitude:
            raise HTTPException(status_code=400, detail="GPS location required")
    
    submission = FormSubmission(
        template_id=data.template_id,
        template_name=template['name'],
        submitted_by=user.id,
        submitted_by_name=user.full_name,
        location_id=template.get('location_id'),
        values=data.values,
        attachments=data.attachments,
        signature_data=data.signature_data,
        signature_timestamp=datetime.now(timezone.utc) if data.signature_data else None,
        gps_latitude=data.gps_latitude,
        gps_longitude=data.gps_longitude,
        gps_accuracy=data.gps_accuracy,
        gps_timestamp=datetime.now(timezone.utc) if data.gps_latitude else None,
        status=data.status,
        submitted_at=datetime.now(timezone.utc) if data.status == FormSubmissionStatus.SUBMITTED else None,
        related_type=data.related_type,
        related_id=data.related_id
    )
    
    doc = submission.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['status'] = doc['status'].value
    if doc['signature_timestamp']:
        doc['signature_timestamp'] = doc['signature_timestamp'].isoformat()
    if doc['gps_timestamp']:
        doc['gps_timestamp'] = doc['gps_timestamp'].isoformat()
    if doc['submitted_at']:
        doc['submitted_at'] = doc['submitted_at'].isoformat()
    
    await db.form_submissions.insert_one(doc)
    
    # Trigger notifications if submitted
    if data.status == FormSubmissionStatus.SUBMITTED and template.get('notify_on_submit'):
        # Queue notifications (handled by automation service)
        from automation_service import AutomationService
        automation = AutomationService(db)
        await automation.log_event(
            event_type="form.submitted",
            event_source="form",
            source_id=submission.id,
            user_id=user.id,
            data={
                "template_id": data.template_id,
                "template_name": template['name'],
                "submitted_by_name": user.full_name,
                "notify_users": template['notify_on_submit']
            }
        )
    
    return FormSubmissionResponse(**submission.model_dump())


@router.patch("/submissions/{submission_id}", response_model=FormSubmissionResponse)
async def update_form_submission(
    submission_id: str,
    updates: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update a form submission (draft) or submit it"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    submission = await db.form_submissions.find_one({"id": submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Form submission not found")
    
    # Check access
    if user.role == UserRole.STAFF and submission['submitted_by'] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if editable
    template = await db.form_templates.find_one({"id": submission['template_id']}, {"_id": 0})
    if submission['status'] != 'draft' and not template.get('allow_edit_after_submit'):
        raise HTTPException(status_code=400, detail="Cannot edit submitted form")
    
    # Handle status change to submitted
    if updates.get('status') == 'submitted' and submission['status'] == 'draft':
        updates['submitted_at'] = datetime.now(timezone.utc).isoformat()
    
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.form_submissions.update_one(
        {"id": submission_id},
        {"$set": updates}
    )
    
    updated = await db.form_submissions.find_one({"id": submission_id}, {"_id": 0})
    return FormSubmissionResponse(**updated)


@router.post("/submissions/{submission_id}/review")
async def review_form_submission(
    submission_id: str,
    status: str,  # approved or rejected
    notes: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Review (approve/reject) a form submission (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if status not in ['approved', 'rejected']:
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")
    
    result = await db.form_submissions.update_one(
        {"id": submission_id},
        {"$set": {
            "status": status,
            "reviewed_by": user.id,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "review_notes": notes,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Form submission not found")
    
    return {"message": f"Form submission {status}"}


# ==================== TASK TEMPLATES ====================

@router.get("/task-templates", response_model=List[TaskTemplateResponse])
async def list_task_templates(
    category: Optional[str] = None,
    is_active: bool = True,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List task templates"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    query = {"is_active": is_active}
    if category:
        query["category"] = category
    
    templates = await db.task_templates.find(query, {"_id": 0}).to_list(100)
    return [TaskTemplateResponse(**t) for t in templates]


@router.post("/task-templates", response_model=TaskTemplateResponse)
async def create_task_template(
    data: TaskTemplateCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a task template (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    template = TaskTemplate(**data.model_dump())
    doc = template.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.task_templates.insert_one(doc)
    return TaskTemplateResponse(**template.model_dump())


@router.patch("/task-templates/{template_id}", response_model=TaskTemplateResponse)
async def update_task_template(
    template_id: str,
    updates: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update a task template (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    result = await db.task_templates.update_one(
        {"id": template_id},
        {"$set": updates}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task template not found")
    
    template = await db.task_templates.find_one({"id": template_id}, {"_id": 0})
    return TaskTemplateResponse(**template)


@router.post("/task-templates/{template_id}/create-task")
async def create_task_from_template(
    template_id: str,
    assigned_to: Optional[str] = None,
    due_date: Optional[str] = None,
    location_id: Optional[str] = None,
    shift_id: Optional[str] = None,
    booking_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a task from a template"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    if user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    template = await db.task_templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Task template not found")
    
    # Determine assignee
    target_user = None
    if assigned_to:
        target_user = await db.users.find_one({"id": assigned_to}, {"_id": 0})
    elif template.get('assign_to_staff_id'):
        target_user = await db.users.find_one({"id": template['assign_to_staff_id']}, {"_id": 0})
    
    # Calculate due date
    task_due_date = None
    if due_date:
        task_due_date = datetime.fromisoformat(due_date)
    elif template.get('default_due_hours'):
        task_due_date = datetime.now(timezone.utc) + timedelta(hours=template['default_due_hours'])
    
    task = EnhancedTask(
        title=template['name'],
        description=template.get('description'),
        location_id=location_id or template.get('location_id') or 'main',
        template_id=template_id,
        assigned_to=target_user['id'] if target_user else None,
        assigned_to_name=target_user['full_name'] if target_user else None,
        assigned_to_role=template.get('assign_to_role'),
        assigned_to_team=template.get('assign_to_team'),
        assigned_by=user.id,
        due_date=task_due_date,
        checklist_items=template.get('checklist_items', []),
        priority=template.get('priority', 'medium'),
        shift_id=shift_id,
        booking_id=booking_id,
        tags=template.get('tags', [])
    )
    
    doc = task.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['status'] = doc['status'].value
    if doc['due_date']:
        doc['due_date'] = doc['due_date'].isoformat()
    
    await db.enhanced_tasks.insert_one(doc)
    
    return {"message": "Task created", "task_id": task.id}


# ==================== ANALYTICS ====================

@router.get("/analytics/submissions")
async def get_submission_analytics(
    template_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get form submission analytics (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if template_id:
        query["template_id"] = template_id
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = end_date
        else:
            query["created_at"] = {"$lte": end_date}
    
    submissions = await db.form_submissions.find(query, {"_id": 0}).to_list(10000)
    
    # Calculate analytics
    total = len(submissions)
    by_status = {}
    by_template = {}
    by_date = {}
    
    for sub in submissions:
        # By status
        status = sub.get('status', 'unknown')
        by_status[status] = by_status.get(status, 0) + 1
        
        # By template
        template_name = sub.get('template_name', 'Unknown')
        by_template[template_name] = by_template.get(template_name, 0) + 1
        
        # By date
        created = sub.get('created_at', '')[:10]
        by_date[created] = by_date.get(created, 0) + 1
    
    return {
        "total_submissions": total,
        "by_status": by_status,
        "by_template": by_template,
        "by_date": dict(sorted(by_date.items())[-30:])  # Last 30 days
    }


@router.get("/analytics/tasks")
async def get_task_analytics(
    template_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get task completion analytics (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if template_id:
        query["template_id"] = template_id
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = end_date
        else:
            query["created_at"] = {"$lte": end_date}
    
    # Try enhanced_tasks first, fall back to tasks
    tasks = await db.enhanced_tasks.find(query, {"_id": 0}).to_list(10000)
    if not tasks:
        tasks = await db.tasks.find(query, {"_id": 0}).to_list(10000)
    
    total = len(tasks)
    completed = sum(1 for t in tasks if t.get('status') == 'completed')
    pending = sum(1 for t in tasks if t.get('status') == 'pending')
    in_progress = sum(1 for t in tasks if t.get('status') == 'in_progress')
    overdue = sum(1 for t in tasks if t.get('due_date') and t.get('status') != 'completed' and t['due_date'] < datetime.now(timezone.utc).isoformat())
    
    return {
        "total_tasks": total,
        "completed": completed,
        "pending": pending,
        "in_progress": in_progress,
        "overdue": overdue,
        "completion_rate": round(completed / total * 100, 1) if total > 0 else 0
    }
