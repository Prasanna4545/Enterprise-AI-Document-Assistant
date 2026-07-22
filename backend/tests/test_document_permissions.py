import os
import sys
import asyncio
import pytest
import uuid
import json
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.base import Base
from app.models.models import (
    Organization, User, UserRole, Document, DocumentChunk, DocumentStatus, AccessLevel, DocumentPermission
)
from app.services.ingestion import DocumentIngestionService
from app.services.embeddings import EmbeddingService
from app.services.vector_store import VectorStoreService
from app.services.retrieval import RetrievalService
from app.services.rag_pipeline import RAGPipelineService

TEST_DB_URL = "sqlite+aiosqlite:///./test_doc_permissions.db"


@pytest.mark.asyncio
async def test_document_level_permissions_isolation():
    """
    Integration Test:
    Confirms that a Manager-restricted document is completely invisible in both
    vector search results and RAG chat answers for an Employee-role user,
    while remaining fully accessible to a Manager-role user.
    """
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # 1. Seed Org, Admin, Manager, and Employee users
    async with async_session() as session:
        org = Organization(id=str(uuid.uuid4()), name="Permission Security Org")
        session.add(org)
        await session.flush()

        admin_user = User(
            id=str(uuid.uuid4()),
            org_id=org.id,
            email="admin@perm.com",
            hashed_password="hashed_pwd",
            full_name="Alice Admin",
            role=UserRole.ADMIN
        )
        manager_user = User(
            id=str(uuid.uuid4()),
            org_id=org.id,
            email="manager@perm.com",
            hashed_password="hashed_pwd",
            full_name="Bob Manager",
            role=UserRole.MANAGER
        )
        employee_user = User(
            id=str(uuid.uuid4()),
            org_id=org.id,
            email="employee@perm.com",
            hashed_password="hashed_pwd",
            full_name="Charlie Employee",
            role=UserRole.EMPLOYEE
        )

        session.add_all([admin_user, manager_user, employee_user])
        await session.commit()

        org_id = org.id
        admin_id = admin_user.id
        manager_id = manager_user.id
        employee_id = employee_user.id

    # 2. Ingest Document A (Public Document)
    doc_public_id = str(uuid.uuid4())
    public_content = "Acme Public General Employee Guide: Work hours are 9 AM to 5 PM Monday through Friday."
    public_embedding = EmbeddingService.get_embedding(public_content)

    # 3. Ingest Document B (Confidential Executive Compensation - Managers Only)
    doc_restricted_id = str(uuid.uuid4())
    restricted_content = "CONFIDENTIAL EXECUTIVE STRATEGY: Manager bonus pool is $250,000 USD for FY2026."
    restricted_embedding = EmbeddingService.get_embedding(restricted_content)

    vector_store = VectorStoreService()

    async with async_session() as session:
        doc_pub = Document(
            id=doc_public_id,
            org_id=org_id,
            uploaded_by_user_id=admin_id,
            title="Public General Guide",
            filename="public_guide.txt",
            file_path="/tmp/public_guide.txt",
            file_type="txt",
            file_size=len(public_content),
            status=DocumentStatus.COMPLETED,
            chunk_count=1,
            access_level=AccessLevel.PUBLIC
        )
        doc_rest = Document(
            id=doc_restricted_id,
            org_id=org_id,
            uploaded_by_user_id=admin_id,
            title="Executive Strategy & Bonus Pool",
            filename="exec_strategy.txt",
            file_path="/tmp/exec_strategy.txt",
            file_type="txt",
            file_size=len(restricted_content),
            status=DocumentStatus.COMPLETED,
            chunk_count=1,
            access_level=AccessLevel.MANAGERS_ONLY
        )
        session.add_all([doc_pub, doc_rest])

        # Store chunks in DB
        chunk_pub = DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=doc_public_id,
            org_id=org_id,
            chunk_index=0,
            content=public_content,
            token_count=20,
            page_number=1,
            vector_id=f"vec_pub_{doc_public_id}",
            metadata_json={"document_id": doc_public_id, "org_id": org_id, "access_level": "PUBLIC"}
        )
        chunk_rest = DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=doc_restricted_id,
            org_id=org_id,
            chunk_index=0,
            content=restricted_content,
            token_count=20,
            page_number=1,
            vector_id=f"vec_rest_{doc_restricted_id}",
            metadata_json={"document_id": doc_restricted_id, "org_id": org_id, "access_level": "MANAGERS_ONLY"}
        )
        session.add_all([chunk_pub, chunk_rest])
        await session.commit()

        # Upsert vectors to ChromaDB
        vector_store.upsert_chunks(
            chunk_ids=[chunk_pub.vector_id, chunk_rest.vector_id],
            embeddings=[public_embedding, restricted_embedding],
            documents=[public_content, restricted_content],
            metadatas=[chunk_pub.metadata_json, chunk_rest.metadata_json]
        )

    # 4. Test Query as EMPLOYEE (Charlie)
    query_str = "What is the manager bonus pool amount for FY2026?"

    async with async_session() as session:
        emp_user_obj = (await session.execute(select(User).where(User.id == employee_id))).scalar_one()

        # Compute accessible document IDs for Employee
        emp_accessible_ids = await RetrievalService.get_user_accessible_document_ids(session, emp_user_obj)
        
        # VERIFICATION 1: Restricted Document ID is NOT in Employee's accessible list
        assert doc_public_id in emp_accessible_ids
        assert doc_restricted_id not in emp_accessible_ids

        # VERIFICATION 2: Vector Store query with Employee permissions returns ZERO chunks from Restricted Document
        emp_retrieved = await RetrievalService.retrieve_relevant_chunks(
            query=query_str,
            user=emp_user_obj,
            db=session,
            top_k=5
        )
        
        retrieved_doc_ids = [c["document_id"] for c in emp_retrieved]
        assert doc_restricted_id not in retrieved_doc_ids
        for c in emp_retrieved:
            assert "$250,000" not in c["content"]

        # VERIFICATION 3: Streaming RAG chat answer for Employee does NOT leak restricted content or citations
        full_answer = ""
        citations = []
        async for evt in RAGPipelineService.stream_rag_response(query=query_str, chunks=emp_retrieved):
            if evt.startswith("data: "):
                payload = json.loads(evt[6:].strip())
                if payload.get("type") == "content":
                    full_answer += payload.get("text", "")
                elif payload.get("type") == "citations":
                    citations = payload.get("citations", [])

        assert "$250,000" not in full_answer
        for cit in citations:
            assert cit["document_id"] != doc_restricted_id

    # 5. Test Query as MANAGER (Bob)
    async with async_session() as session:
        mgr_user_obj = (await session.execute(select(User).where(User.id == manager_id))).scalar_one()

        mgr_accessible_ids = await RetrievalService.get_user_accessible_document_ids(session, mgr_user_obj)
        
        # VERIFICATION 4: Restricted Document ID IS in Manager's accessible list
        assert doc_restricted_id in mgr_accessible_ids

        # VERIFICATION 5: Vector Store query returns Restricted Document chunks for Manager
        mgr_retrieved = await RetrievalService.retrieve_relevant_chunks(
            query=query_str,
            user=mgr_user_obj,
            db=session,
            top_k=5
        )
        
        mgr_doc_ids = [c["document_id"] for c in mgr_retrieved]
        assert doc_restricted_id in mgr_doc_ids
        assert any("$250,000" in c["content"] for c in mgr_retrieved)
