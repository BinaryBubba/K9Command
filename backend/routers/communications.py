"""
Communications & Training Router - Connecteam Parity
Handles announcements, acknowledgements, training courses, quizzes, knowledge base
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from datetime import datetime, timezone

from models import (
    UserRole,
    Announcement, AnnouncementCreate, AnnouncementResponse, AnnouncementPriority,
    Acknowledgement,
    Course, CourseCreate, CourseResponse, CourseStatus,
    Quiz, QuizCreate, QuizResponse, QuizAttempt, CourseProgress,
    KnowledgeArticle, KnowledgeArticleCreate, KnowledgeArticleResponse,
)
from auth import get_current_user

router = APIRouter(prefix="/api/comms", tags=["Communications & Training"])
security = HTTPBearer()


def get_db():
    """Get database connection - will be injected"""
    from server import db
    return db


# ==================== ANNOUNCEMENTS ====================

@router.get("/announcements", response_model=List[AnnouncementResponse])
async def list_announcements(
    status: str = "published",
    priority: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List announcements visible to current user"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    query = {"status": status}
    
    if priority:
        query["priority"] = priority
    
    # Filter by targeting (if not admin)
    if user.role != UserRole.ADMIN:
        query["$or"] = [
            {"target_roles": {"$size": 0}},  # No targeting = all
            {"target_roles": user.role.value},
            {"target_staff_ids": user.id}
        ]
    
    # Filter expired
    now = datetime.now(timezone.utc).isoformat()
    query["$and"] = [
        {"$or": [{"expires_at": None}, {"expires_at": {"$gt": now}}]},
        {"$or": [{"publish_at": None}, {"publish_at": {"$lte": now}}]}
    ]
    
    announcements = await db.announcements.find(query, {"_id": 0}).sort([
        ("is_pinned", -1),
        ("priority", -1),
        ("published_at", -1)
    ]).to_list(100)
    
    return [AnnouncementResponse(**a) for a in announcements]


@router.get("/announcements/{announcement_id}", response_model=AnnouncementResponse)
async def get_announcement(
    announcement_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a single announcement"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    announcement = await db.announcements.find_one({"id": announcement_id}, {"_id": 0})
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Increment view count
    await db.announcements.update_one(
        {"id": announcement_id},
        {"$inc": {"view_count": 1}}
    )
    
    return AnnouncementResponse(**announcement)


@router.post("/announcements", response_model=AnnouncementResponse)
async def create_announcement(
    data: AnnouncementCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create an announcement (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    announcement = Announcement(
        title=data.title,
        content=data.content,
        author_id=user.id,
        author_name=user.full_name,
        location_id=data.location_id,
        target_roles=data.target_roles,
        target_teams=data.target_teams,
        target_staff_ids=data.target_staff_ids,
        priority=data.priority,
        is_pinned=data.is_pinned,
        requires_acknowledgement=data.requires_acknowledgement,
        acknowledgement_deadline=data.acknowledgement_deadline,
        publish_at=data.publish_at,
        expires_at=data.expires_at,
        status=data.status,
        published_at=datetime.now(timezone.utc) if data.status == "published" else None,
        attachments=data.attachments
    )
    
    doc = announcement.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['priority'] = doc['priority'].value
    if doc['acknowledgement_deadline']:
        doc['acknowledgement_deadline'] = doc['acknowledgement_deadline'].isoformat()
    if doc['publish_at']:
        doc['publish_at'] = doc['publish_at'].isoformat()
    if doc['expires_at']:
        doc['expires_at'] = doc['expires_at'].isoformat()
    if doc['published_at']:
        doc['published_at'] = doc['published_at'].isoformat()
    
    await db.announcements.insert_one(doc)
    
    # Trigger notifications if published
    if data.status == "published":
        from automation_service import AutomationService
        automation = AutomationService(db)
        await automation.log_event(
            event_type="announcement.published",
            event_source="communications",
            source_id=announcement.id,
            user_id=user.id,
            data={
                "title": data.title,
                "priority": data.priority.value,
                "requires_acknowledgement": data.requires_acknowledgement,
                "target_roles": data.target_roles,
                "target_staff_ids": data.target_staff_ids
            }
        )
    
    return AnnouncementResponse(**announcement.model_dump())


@router.patch("/announcements/{announcement_id}", response_model=AnnouncementResponse)
async def update_announcement(
    announcement_id: str,
    updates: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update an announcement (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    existing = await db.announcements.find_one({"id": announcement_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Handle status change to published
    if updates.get('status') == 'published' and existing.get('status') != 'published':
        updates['published_at'] = datetime.now(timezone.utc).isoformat()
    
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.announcements.update_one(
        {"id": announcement_id},
        {"$set": updates}
    )
    
    announcement = await db.announcements.find_one({"id": announcement_id}, {"_id": 0})
    return AnnouncementResponse(**announcement)


@router.delete("/announcements/{announcement_id}")
async def delete_announcement(
    announcement_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Archive an announcement (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.announcements.update_one(
        {"id": announcement_id},
        {"$set": {"status": "archived", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement archived"}


# ==================== ACKNOWLEDGEMENTS ====================

@router.post("/announcements/{announcement_id}/acknowledge")
async def acknowledge_announcement(
    announcement_id: str,
    confirmation_text: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Acknowledge an announcement"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    announcement = await db.announcements.find_one({"id": announcement_id}, {"_id": 0})
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Check if already acknowledged
    existing = await db.acknowledgements.find_one({
        "announcement_id": announcement_id,
        "staff_id": user.id
    }, {"_id": 0})
    
    if existing:
        return {"message": "Already acknowledged", "acknowledged_at": existing.get('acknowledged_at')}
    
    ack = Acknowledgement(
        announcement_id=announcement_id,
        staff_id=user.id,
        staff_name=user.full_name,
        confirmation_text=confirmation_text
    )
    
    doc = ack.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['acknowledged_at'] = doc['acknowledged_at'].isoformat()
    
    await db.acknowledgements.insert_one(doc)
    
    # Increment acknowledgement count
    await db.announcements.update_one(
        {"id": announcement_id},
        {"$inc": {"acknowledgement_count": 1}}
    )
    
    return {"message": "Announcement acknowledged", "acknowledged_at": ack.acknowledged_at.isoformat()}


@router.get("/announcements/{announcement_id}/acknowledgements")
async def list_acknowledgements(
    announcement_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List who has acknowledged an announcement (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    acks = await db.acknowledgements.find(
        {"announcement_id": announcement_id}, {"_id": 0}
    ).to_list(1000)
    
    # Get total target count
    announcement = await db.announcements.find_one({"id": announcement_id}, {"_id": 0})
    
    return {
        "announcement_id": announcement_id,
        "total_acknowledged": len(acks),
        "requires_acknowledgement": announcement.get('requires_acknowledgement', False) if announcement else False,
        "acknowledgements": acks
    }


@router.get("/announcements/pending-acknowledgements")
async def get_pending_acknowledgements(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get announcements pending acknowledgement for current user"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    # Get user's acknowledgements
    user_acks = await db.acknowledgements.find(
        {"staff_id": user.id}, {"_id": 0}
    ).to_list(1000)
    acked_ids = [a['announcement_id'] for a in user_acks]
    
    # Get announcements requiring acknowledgement
    now = datetime.now(timezone.utc).isoformat()
    query = {
        "status": "published",
        "requires_acknowledgement": True,
        "id": {"$nin": acked_ids},
        "$or": [
            {"target_roles": {"$size": 0}},
            {"target_roles": user.role.value},
            {"target_staff_ids": user.id}
        ]
    }
    
    pending = await db.announcements.find(query, {"_id": 0}).to_list(100)
    
    return {
        "pending_count": len(pending),
        "announcements": [AnnouncementResponse(**a) for a in pending]
    }


# ==================== TRAINING COURSES ====================

@router.get("/courses", response_model=List[CourseResponse])
async def list_courses(
    status: str = "published",
    category: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List training courses"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    query = {"status": status}
    if category:
        query["category"] = category
    
    # For non-admins, filter by required roles
    if user.role != UserRole.ADMIN:
        query["$or"] = [
            {"required_for_roles": {"$size": 0}},
            {"required_for_roles": user.role.value}
        ]
    
    courses = await db.courses.find(query, {"_id": 0}).to_list(100)
    return [CourseResponse(**c) for c in courses]


@router.get("/courses/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a single course"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return CourseResponse(**course)


@router.post("/courses", response_model=CourseResponse)
async def create_course(
    data: CourseCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a training course (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    course = Course(**data.model_dump())
    doc = course.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['status'] = doc['status'].value
    if doc['due_date']:
        doc['due_date'] = doc['due_date'].isoformat()
    
    await db.courses.insert_one(doc)
    return CourseResponse(**course.model_dump())


@router.patch("/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    updates: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update a course (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    existing = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Course not found")
    
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    updates['version'] = existing.get('version', 1) + 1
    
    await db.courses.update_one(
        {"id": course_id},
        {"$set": updates}
    )
    
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    return CourseResponse(**course)


# ==================== COURSE PROGRESS ====================

@router.get("/courses/{course_id}/progress")
async def get_my_course_progress(
    course_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get current user's progress on a course"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    progress = await db.course_progress.find_one({
        "course_id": course_id,
        "staff_id": user.id
    }, {"_id": 0})
    
    if not progress:
        return {
            "course_id": course_id,
            "staff_id": user.id,
            "status": "not_started",
            "progress_percentage": 0
        }
    
    return progress


@router.post("/courses/{course_id}/start")
async def start_course(
    course_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Start a course"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if already started
    existing = await db.course_progress.find_one({
        "course_id": course_id,
        "staff_id": user.id
    }, {"_id": 0})
    
    if existing:
        return {"message": "Course already started", "progress": existing}
    
    progress = CourseProgress(
        course_id=course_id,
        staff_id=user.id,
        staff_name=user.full_name,
        status="in_progress",
        started_at=datetime.now(timezone.utc)
    )
    
    doc = progress.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['started_at'] = doc['started_at'].isoformat()
    
    await db.course_progress.insert_one(doc)
    
    return {"message": "Course started", "progress_id": progress.id}


@router.post("/courses/{course_id}/complete-section")
async def complete_section(
    course_id: str,
    section_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Mark a course section as complete"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    progress = await db.course_progress.find_one({
        "course_id": course_id,
        "staff_id": user.id
    }, {"_id": 0})
    
    if not progress:
        raise HTTPException(status_code=400, detail="Course not started")
    
    sections_completed = progress.get('sections_completed', [])
    if section_id not in sections_completed:
        sections_completed.append(section_id)
    
    total_sections = len(course.get('sections', []))
    progress_percentage = (len(sections_completed) / total_sections * 100) if total_sections > 0 else 100
    
    status = "completed" if progress_percentage >= 100 else "in_progress"
    
    await db.course_progress.update_one(
        {"course_id": course_id, "staff_id": user.id},
        {"$set": {
            "sections_completed": sections_completed,
            "progress_percentage": progress_percentage,
            "status": status,
            "completed_at": datetime.now(timezone.utc).isoformat() if status == "completed" else None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": "Section completed",
        "progress_percentage": progress_percentage,
        "status": status
    }


# ==================== QUIZZES ====================

@router.get("/quizzes/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a quiz (questions without correct answers for non-admins)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    quiz = await db.quizzes.find_one({"id": quiz_id}, {"_id": 0})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Remove correct answers for non-admins
    if user.role != UserRole.ADMIN:
        for q in quiz.get('questions', []):
            q.pop('correct_answer', None)
    
    return QuizResponse(**quiz)


@router.post("/quizzes", response_model=QuizResponse)
async def create_quiz(
    data: QuizCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a quiz (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    quiz = Quiz(**data.model_dump())
    doc = quiz.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.quizzes.insert_one(doc)
    
    # Link to course if specified
    if data.course_id:
        await db.courses.update_one(
            {"id": data.course_id},
            {"$set": {"quiz_id": quiz.id, "has_quiz": True}}
        )
    
    return QuizResponse(**quiz.model_dump())


@router.post("/quizzes/{quiz_id}/submit")
async def submit_quiz(
    quiz_id: str,
    answers: dict,  # question_id -> answer
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Submit quiz answers"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    quiz = await db.quizzes.find_one({"id": quiz_id}, {"_id": 0})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Check max attempts
    attempts = await db.quiz_attempts.count_documents({
        "quiz_id": quiz_id,
        "staff_id": user.id
    })
    
    if quiz.get('max_attempts') and attempts >= quiz['max_attempts']:
        raise HTTPException(status_code=400, detail="Maximum attempts reached")
    
    # Grade quiz
    questions = quiz.get('questions', [])
    correct = 0
    total = len(questions)
    
    for q in questions:
        q_id = q.get('id')
        if q_id and answers.get(q_id) == q.get('correct_answer'):
            correct += 1
    
    score = (correct / total * 100) if total > 0 else 0
    passed = score >= quiz.get('passing_score', 70)
    
    attempt = QuizAttempt(
        quiz_id=quiz_id,
        staff_id=user.id,
        staff_name=user.full_name,
        answers=answers,
        score=score,
        passed=passed,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        attempt_number=attempts + 1
    )
    
    doc = attempt.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    doc['started_at'] = doc['started_at'].isoformat()
    doc['completed_at'] = doc['completed_at'].isoformat()
    
    await db.quiz_attempts.insert_one(doc)
    
    # Update course progress if linked
    if quiz.get('course_id'):
        await db.course_progress.update_one(
            {"course_id": quiz['course_id'], "staff_id": user.id},
            {"$set": {
                "quiz_passed": passed,
                "best_quiz_score": max(score, 0),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            "$inc": {"quiz_attempts": 1}},
            upsert=True
        )
    
    result = {
        "score": score,
        "passed": passed,
        "correct_answers": correct,
        "total_questions": total,
        "attempt_number": attempts + 1
    }
    
    if quiz.get('show_correct_answers'):
        result["correct_answers_detail"] = {q['id']: q.get('correct_answer') for q in questions if 'id' in q}
    
    return result


# ==================== KNOWLEDGE BASE ====================

@router.get("/knowledge", response_model=List[KnowledgeArticleResponse])
async def list_knowledge_articles(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List knowledge base articles"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    query = {"status": "published"}
    
    if category:
        query["category"] = category
    
    if tag:
        query["tags"] = tag
    
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"content": {"$regex": search, "$options": "i"}},
            {"search_keywords": {"$regex": search, "$options": "i"}}
        ]
    
    # Filter by visibility
    if user.role != UserRole.ADMIN:
        query["$and"] = query.get("$and", []) + [
            {"$or": [
                {"visible_to_roles": {"$size": 0}},
                {"visible_to_roles": user.role.value}
            ]}
        ]
    
    articles = await db.knowledge_articles.find(query, {"_id": 0}).sort("updated_at", -1).to_list(100)
    return [KnowledgeArticleResponse(**a) for a in articles]


@router.get("/knowledge/{article_id}", response_model=KnowledgeArticleResponse)
async def get_knowledge_article(
    article_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a knowledge base article"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    article = await db.knowledge_articles.find_one({"id": article_id}, {"_id": 0})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return KnowledgeArticleResponse(**article)


@router.post("/knowledge", response_model=KnowledgeArticleResponse)
async def create_knowledge_article(
    data: KnowledgeArticleCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a knowledge base article (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    article = KnowledgeArticle(
        title=data.title,
        content=data.content,
        location_id=data.location_id,
        category=data.category,
        tags=data.tags,
        visible_to_roles=data.visible_to_roles,
        status=data.status,
        search_keywords=data.search_keywords,
        attachments=data.attachments,
        author_id=user.id,
        author_name=user.full_name
    )
    
    doc = article.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.knowledge_articles.insert_one(doc)
    return KnowledgeArticleResponse(**article.model_dump())


@router.patch("/knowledge/{article_id}", response_model=KnowledgeArticleResponse)
async def update_knowledge_article(
    article_id: str,
    updates: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update a knowledge base article (admin only)"""
    db = get_db()
    user = await get_current_user(credentials, db)
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    existing = await db.knowledge_articles.find_one({"id": article_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Track revision
    revision = {
        "version": existing.get('version', 1),
        "updated_by": user.id,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    updates['version'] = existing.get('version', 1) + 1
    updates['last_updated_by'] = user.id
    
    await db.knowledge_articles.update_one(
        {"id": article_id},
        {
            "$set": updates,
            "$push": {"revision_history": revision}
        }
    )
    
    article = await db.knowledge_articles.find_one({"id": article_id}, {"_id": 0})
    return KnowledgeArticleResponse(**article)


@router.get("/knowledge/categories/list")
async def list_knowledge_categories(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get list of knowledge base categories"""
    db = get_db()
    user = await get_current_user(credentials, db)
    
    articles = await db.knowledge_articles.find(
        {"status": "published"},
        {"category": 1, "_id": 0}
    ).to_list(1000)
    
    categories = list(set(a.get('category') for a in articles if a.get('category')))
    return {"categories": sorted(categories)}
