import json
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.models import User, ChatSession, Message, MessageSender
from app.schemas.schemas import (
    ChatSessionCreate, ChatSessionResponse, MessageResponse, RAGQueryRequest,
    MessageFeedbackRequest, MessageFeedbackResponse
)

from app.services.retrieval import RetrievalService
from app.services.rag_pipeline import RAGPipelineService
from app.services.analytics_service import AnalyticsService
from app.core.rate_limiter import RateLimiter

router = APIRouter(prefix="/chat", tags=["Chat & RAG"])



@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    payload: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Creates a new Chat Session for the current user."""
    session = ChatSession(
        org_id=current_user.org_id,
        user_id=current_user.id,
        title=payload.title or "New Chat"
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists all chat sessions belonging to the authenticated user."""
    stmt = select(ChatSession).where(
        ChatSession.org_id == current_user.org_id,
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.updated_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves message history for a specific chat session."""
    stmt = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.org_id == current_user.org_id,
        ChatSession.user_id == current_user.id
    )
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    msg_stmt = select(Message).where(Message.session_id == session_id).order_by(Message.created_at.asc())
    msg_res = await db.execute(msg_stmt)
    return msg_res.scalars().all()


@router.post("/query/stream", dependencies=[Depends(RateLimiter("chat_query"))])
async def stream_rag_query(
    payload: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    RAG Streaming Endpoint:
    1. Validates chat session.
    2. Saves User message.
    3. Retrieves top-k document chunks scoped by tenant org_id and user role.
    4. Streams answer tokens via SSE (Server-Sent Events) and yields citations payload.
    5. Saves Assistant message with citations payload to DB upon completion.
    """
    stmt = select(ChatSession).where(
        ChatSession.id == payload.session_id,
        ChatSession.org_id == current_user.org_id,
        ChatSession.user_id == current_user.id
    )
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    # Save User message to DB
    user_msg = Message(
        session_id=session.id,
        sender=MessageSender.USER,
        content=payload.query
    )
    db.add(user_msg)
    await db.commit()

    # Update session title if first query
    if session.title == "New Chat":
        session.title = payload.query[:40] + ("..." if len(payload.query) > 40 else "")
        await db.commit()

    # Fetch recent chat history
    msg_stmt = select(Message).where(Message.session_id == session.id).order_by(Message.created_at.asc())
    history_res = await db.execute(msg_stmt)
    history_msgs = history_res.scalars().all()
    history_formatted = [{"sender": m.sender.value, "content": m.content} for m in history_msgs[:-1]]

    # Step 1: Retrieve context chunks
    chunks = await RetrievalService.retrieve_relevant_chunks(
        query=payload.query,
        user=current_user,
        db=db,
        top_k=6
    )

    # Log audit
    await AnalyticsService.log_action(
        db=db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        action="RAG_QUERY",
        resource_type="CHAT_SESSION",
        resource_id=session.id,
        metadata_json={"query": payload.query, "retrieved_chunks_count": len(chunks)}
    )

    # Prepare streaming response wrapper that saves Assistant message at the end
    async def sse_event_generator():
        full_assistant_text = ""
        citations_data = []

        async for chunk_evt in RAGPipelineService.stream_rag_response(
            query=payload.query,
            chunks=chunks,
            chat_history=history_formatted
        ):
            yield chunk_evt
            
            # Extract content text and citations payload for DB persistence
            if chunk_evt.startswith("data: "):
                try:
                    payload_data = json.loads(chunk_evt[6:].strip())
                    if payload_data.get("type") == "content":
                        full_assistant_text += payload_data.get("text", "")
                    elif payload_data.get("type") == "citations":
                        citations_data = payload_data.get("citations", [])
                except Exception:
                    pass

        # Save Assistant message to DB
        try:
            assistant_msg = Message(
                session_id=session.id,
                sender=MessageSender.ASSISTANT,
                content=full_assistant_text,
                citations=citations_data
            )
            db.add(assistant_msg)
            await db.commit()
        except Exception:
            pass

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")


@router.post("/messages/{message_id}/feedback", response_model=MessageFeedbackResponse)
async def submit_message_feedback(
    message_id: str,
    payload: MessageFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submits or updates thumbs up/down rating for an Assistant message.
    Upserts existing feedback if duplicate vote by same user on same message.
    Stores retrieved chunk IDs to enable tracing answer quality.
    """
    from app.models.models import MessageFeedback
    from app.schemas.schemas import MessageFeedbackResponse

    stmt = select(Message).where(Message.id == message_id)
    res = await db.execute(stmt)
    msg = res.scalar_one_or_none()

    if not msg:
        raise HTTPException(status_code=404, detail="Message not found.")

    # Validate chat session belongs to user's org
    sess_stmt = select(ChatSession).where(ChatSession.id == msg.session_id, ChatSession.org_id == current_user.org_id)
    sess_res = await db.execute(sess_stmt)
    session = sess_res.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=403, detail="Access denied to message session.")

    # Extract retrieved chunk IDs/metadata from message citations
    retrieved_chunk_ids = []
    if msg.citations:
        retrieved_chunk_ids = msg.citations

    # Check for existing feedback record by (message_id, user_id) -> UPSERT
    fb_stmt = select(MessageFeedback).where(
        MessageFeedback.message_id == message_id,
        MessageFeedback.user_id == current_user.id
    )
    fb_res = await db.execute(fb_stmt)
    existing_fb = fb_res.scalar_one_or_none()

    if existing_fb:
        # Update existing vote
        existing_fb.rating = payload.rating
        existing_fb.retrieved_chunk_ids = retrieved_chunk_ids
        existing_fb.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(existing_fb)
        fb_record = existing_fb
    else:
        # Create new vote record
        new_fb = MessageFeedback(
            message_id=message_id,
            user_id=current_user.id,
            org_id=current_user.org_id,
            rating=payload.rating,
            retrieved_chunk_ids=retrieved_chunk_ids
        )
        db.add(new_fb)
        await db.commit()
        await db.refresh(new_fb)
        fb_record = new_fb

    # Log audit
    await AnalyticsService.log_action(
        db=db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        action="MESSAGE_FEEDBACK",
        resource_type="MESSAGE",
        resource_id=message_id,
        metadata_json={"rating": payload.rating.value}
    )

    return fb_record

