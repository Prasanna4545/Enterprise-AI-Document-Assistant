from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.models import User, UserRole, AuditLog
from app.schemas.schemas import UserResponse, UserCreateAdmin, AnalyticsSummaryResponse, AuditLogResponse, NegativeFeedbackDebugItem

from app.core.security import hash_password
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/admin", tags=["Admin & Analytics"])


@router.get("/users", response_model=List[UserResponse])
async def list_org_users(
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Lists all users in the current organization (Admin restricted)."""
    stmt = select(User).where(User.org_id == current_user.org_id).order_by(User.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_in_org(
    payload: UserCreateAdmin,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Creates a new user account within the admin's organization."""
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User with this email already exists.")

    hashed_pwd = hash_password(payload.password)
    new_user = User(
        org_id=current_user.org_id,
        email=payload.email,
        hashed_password=hashed_pwd,
        full_name=payload.full_name,
        role=payload.role
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    await AnalyticsService.log_action(
        db=db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        action="USER_CREATED",
        resource_type="USER",
        resource_id=new_user.id,
        metadata_json={"email": new_user.email, "role": new_user.role.value}
    )

    return new_user


@router.get("/analytics", response_model=AnalyticsSummaryResponse)
async def get_analytics(
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db)
):
    """Returns aggregated analytics metrics for the organization."""
    analytics = await AnalyticsService.get_org_analytics(db, current_user.org_id)
    return analytics


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves organization audit trail logs (Admin restricted)."""
    stmt = select(AuditLog).where(AuditLog.org_id == current_user.org_id).order_by(AuditLog.timestamp.desc()).limit(100)
    res = await db.execute(stmt)
    logs = res.scalars().all()

    # Enrich logs with user email/name
    user_ids = list(set([l.user_id for l in logs if l.user_id]))
    user_map = {}
    if user_ids:
        u_stmt = select(User).where(User.id.in_(user_ids))
        u_res = await db.execute(u_stmt)
        users = u_res.scalars().all()
        user_map = {u.id: {"name": u.full_name, "email": u.email} for u in users}

    response_logs = []
    for log in logs:
        u_info = user_map.get(log.user_id, {})
        response_logs.append(AuditLogResponse(
            id=log.id,
            org_id=log.org_id,
            user_id=log.user_id,
            user_name=u_info.get("name"),
            user_email=u_info.get("email"),
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            metadata_json=log.metadata_json,
            timestamp=log.timestamp
        ))

    return response_logs


@router.get("/negative-feedback", response_model=List[NegativeFeedbackDebugItem])
async def get_negative_feedback_debug_items(
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves all negative feedback (THUMBS_DOWN) entries with side-by-side
    Original User Query, Generated Assistant Answer, and Retrieved Chunk Snippets
    to enable tracing bad answers back to retrieval quality.
    """
    from app.models.models import MessageFeedback, FeedbackRating, Message, ChatSession
    from app.schemas.schemas import NegativeFeedbackDebugItem

    stmt = select(MessageFeedback).where(
        MessageFeedback.org_id == current_user.org_id,
        MessageFeedback.rating == FeedbackRating.THUMBS_DOWN
    ).order_by(MessageFeedback.created_at.desc()).limit(50)

    res = await db.execute(stmt)
    feedbacks = res.scalars().all()

    if not feedbacks:
        return []

    # Fetch messages, sessions, users for enrichment
    msg_ids = [f.message_id for f in feedbacks]
    user_ids = list(set([f.user_id for f in feedbacks]))

    msg_stmt = select(Message).where(Message.id.in_(msg_ids))
    msg_res = await db.execute(msg_stmt)
    msg_map = {m.id: m for m in msg_res.scalars().all()}

    user_stmt = select(User).where(User.id.in_(user_ids))
    user_res = await db.execute(user_stmt)
    user_map = {u.id: u for u in user_res.scalars().all()}

    debug_items = []

    for fb in feedbacks:
        asst_msg = msg_map.get(fb.message_id)
        u_obj = user_map.get(fb.user_id)

        user_query = "Original question not found"
        assistant_answer = asst_msg.content if asst_msg else "No answer content"

        if asst_msg:
            # Fetch preceding USER message in the same chat session
            prev_msg_stmt = select(Message).where(
                Message.session_id == asst_msg.session_id,
                Message.created_at <= asst_msg.created_at,
                Message.sender == "USER"
            ).order_by(Message.created_at.desc()).limit(1)
            prev_res = await db.execute(prev_msg_stmt)
            user_msg = prev_res.scalar_one_or_none()
            if user_msg:
                user_query = user_msg.content

        chunks = fb.retrieved_chunk_ids or []

        debug_items.append(NegativeFeedbackDebugItem(
            feedback_id=fb.id,
            message_id=fb.message_id,
            user_name=u_obj.full_name if u_obj else "Unknown User",
            user_email=u_obj.email if u_obj else "Unknown Email",
            user_query=user_query,
            assistant_answer=assistant_answer,
            rating=fb.rating,
            retrieved_chunks=chunks,
            timestamp=fb.created_at
        ))

    return debug_items

