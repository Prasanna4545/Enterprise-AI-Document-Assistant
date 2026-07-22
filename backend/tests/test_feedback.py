import os
import sys
import uuid
import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, func

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models.models import (
    Base, Organization, User, UserRole, ChatSession, Message, 
    MessageSender, MessageFeedback, FeedbackRating
)
from app.api.chat import submit_message_feedback
from app.api.admin import get_negative_feedback_debug_items
from app.schemas.schemas import MessageFeedbackRequest

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.mark.asyncio
async def test_message_feedback_chunk_linkage_and_upsert():
    """
    Integration Test:
    1. Confirms submitting feedback links message_id, user_id, and retrieved_chunk_ids.
    2. Verifies duplicate votes by the same user on the same message update existing record rather than creating duplicates.
    3. Confirms GET /admin/negative-feedback returns side-by-side debug items.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    org_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    user_msg_id = str(uuid.uuid4())
    asst_msg_id = str(uuid.uuid4())

    chunk_1_id = f"vec_chunk_{uuid.uuid4()}"
    chunk_2_id = f"vec_chunk_{uuid.uuid4()}"

    test_citations = [
        {
            "chunk_id": chunk_1_id,
            "document_id": "doc_101",
            "filename": "Employee_Handbook_2026.pdf",
            "title": "Employee Handbook",
            "page_number": 4,
            "snippet": "Employees receive 20 days of paid annual leave per calendar year."
        },
        {
            "chunk_id": chunk_2_id,
            "document_id": "doc_102",
            "filename": "Benefits_Summary.pdf",
            "title": "Benefits Summary",
            "page_number": 2,
            "snippet": "Health insurance coverage starts on the first day of employment."
        }
    ]

    async with async_session() as session:
        # Seed org, user, session, and messages
        org = Organization(id=org_id, name="Feedback Test Corp")


        user = User(
            id=user_id,
            org_id=org_id,
            email="tester@feedbacktest.com",
            full_name="Tester Employee",
            hashed_password="hashedpassword",
            role=UserRole.EMPLOYEE
        )
        chat_sess = ChatSession(id=session_id, org_id=org_id, user_id=user_id, title="PTO Policy Query")
        
        user_msg = Message(
            id=user_msg_id,
            session_id=session_id,
            sender=MessageSender.USER,
            content="How many days of paid leave do employees get?"
        )
        asst_msg = Message(
            id=asst_msg_id,
            session_id=session_id,
            sender=MessageSender.ASSISTANT,
            content="Employees receive 20 days of paid annual leave per year according to Section 4.",
            citations=test_citations
        )

        session.add_all([org, user, chat_sess, user_msg, asst_msg])
        await session.commit()

    # 1. Submit initial THUMBS_DOWN feedback
    async with async_session() as session:
        user_obj = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
        
        fb_resp = await submit_message_feedback(
            message_id=asst_msg_id,
            payload=MessageFeedbackRequest(rating=FeedbackRating.THUMBS_DOWN),
            current_user=user_obj,
            db=session
        )

        first_fb_id = fb_resp.id
        assert fb_resp.message_id == asst_msg_id
        assert fb_resp.user_id == user_id
        assert fb_resp.rating == FeedbackRating.THUMBS_DOWN
        assert len(fb_resp.retrieved_chunk_ids) == 2
        assert fb_resp.retrieved_chunk_ids[0]["chunk_id"] == chunk_1_id

    # Verify 1 record in DB
    async with async_session() as session:
        count_res = await session.execute(select(func.count(MessageFeedback.id)))
        assert count_res.scalar_one() == 1

    # 2. Submit duplicate vote (THUMBS_UP) on the SAME message by SAME user -> Expect UPSERT
    async with async_session() as session:
        user_obj = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
        
        fb_resp_2 = await submit_message_feedback(
            message_id=asst_msg_id,
            payload=MessageFeedbackRequest(rating=FeedbackRating.THUMBS_UP),
            current_user=user_obj,
            db=session
        )

        # Record ID must match first submission (updated, not duplicated!)
        assert fb_resp_2.id == first_fb_id
        assert fb_resp_2.rating == FeedbackRating.THUMBS_UP

    # Verify total DB count is STILL 1 (No duplicate rows!)
    async with async_session() as session:
        count_res = await session.execute(select(func.count(MessageFeedback.id)))
        assert count_res.scalar_one() == 1

    # 3. Update vote back to THUMBS_DOWN and verify Admin Negative Feedback debug view
    async with async_session() as session:
        user_obj = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
        await submit_message_feedback(
            message_id=asst_msg_id,
            payload=MessageFeedbackRequest(rating=FeedbackRating.THUMBS_DOWN),
            current_user=user_obj,
            db=session
        )

    # Query Admin Debug Endpoint
    async with async_session() as session:
        admin_user = User(
            id=str(uuid.uuid4()),
            org_id=org_id,
            email="admin@feedbacktest.com",
            full_name="Test Admin",
            role=UserRole.ADMIN
        )
        debug_items = await get_negative_feedback_debug_items(current_user=admin_user, db=session)
        
        assert len(debug_items) == 1
        item = debug_items[0]
        assert item.message_id == asst_msg_id
        assert item.user_query == "How many days of paid leave do employees get?"
        assert "20 days of paid annual leave" in item.assistant_answer
        assert len(item.retrieved_chunks) == 2
        assert item.retrieved_chunks[0]["filename"] == "Employee_Handbook_2026.pdf"

    await engine.dispose()
