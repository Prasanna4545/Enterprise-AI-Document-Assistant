import os
import sys
import asyncio
import pytest
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

# Ensure backend root directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.base import Base
from app.models.models import (
    Organization, User, UserRole, Document, DocumentChunk, DocumentStatus, AccessLevel
)
from app.services.ingestion import DocumentIngestionService
from app.services.embeddings import EmbeddingService
from app.services.vector_store import VectorStoreService
from app.services.retrieval import RetrievalService
from app.services.rag_pipeline import RAGPipelineService

TEST_DB_URL = "sqlite+aiosqlite:///./test_rag_integration.db"


@pytest.mark.asyncio
async def test_end_to_end_rag_ingestion_retrieval_and_citation():
    """
    End-to-End Integration Test:
    1. Initializes DB & Seeds Organization & User.
    2. Ingests multi-page PDF fixture (`Acme_Corporate_Policies_2026.pdf`).
    3. Verifies chunking, embedding, vector store upsert, and DB persistence.
    4. Executes vector retrieval queries for distinct policies across Pages 1, 2, and 3.
    5. Asserts correct top-k chunk, page number metadata, and source citations.
    """
    # Step 1: Database Setup
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Step 2: Seed Org & User
    async with async_session() as session:
        org = Organization(id=str(uuid.uuid4()), name="Integration Test Org")
        session.add(org)
        await session.flush()

        user = User(
            id=str(uuid.uuid4()),
            org_id=org.id,
            email="test_user@integration.com",
            hashed_password="hashed_pwd_test",
            full_name="Integration User",
            role=UserRole.ADMIN
        )
        session.add(user)
        await session.commit()
        org_id = org.id
        user_id = user.id

    # Step 3: Parse & Ingest Fixture PDF
    pdf_path = os.path.join(os.path.dirname(__file__), "fixtures", "Acme_Corporate_Policies_2026.pdf")
    assert os.path.exists(pdf_path), f"Fixture file not found at {pdf_path}"

    pages = DocumentIngestionService.parse_file(pdf_path, "pdf")
    assert len(pages) == 3, f"Expected 3 pages in test PDF, got {len(pages)}"

    chunks = DocumentIngestionService.chunk_text(pages, chunk_size_tokens=300, overlap_tokens=40)
    assert len(chunks) >= 3, "Expected at least 3 chunks"

    chunk_texts = [c.content for c in chunks]
    embeddings = EmbeddingService.get_embeddings(chunk_texts)
    assert len(embeddings) == len(chunks)

    # Persist in DB and VectorStore
    async with async_session() as session:
        doc = Document(
            id=str(uuid.uuid4()),
            org_id=org_id,
            uploaded_by_user_id=user_id,
            title="Acme Policy Guide",
            filename="Acme_Corporate_Policies_2026.pdf",
            file_path=pdf_path,
            file_type="pdf",
            file_size=os.path.getsize(pdf_path),
            status=DocumentStatus.COMPLETED,
            chunk_count=len(chunks),
            access_level=AccessLevel.PUBLIC
        )
        session.add(doc)

        vector_store = VectorStoreService()
        chunk_ids = []
        vectors = []
        texts = []
        metadatas = []
        db_chunks = []

        for idx, chunk in enumerate(chunks):
            v_id = f"vec_test_{doc.id}_{idx}"
            chunk_ids.append(v_id)
            vectors.append(embeddings[idx])
            texts.append(chunk.content)
            
            meta = {
                "document_id": doc.id,
                "org_id": org_id,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number or 1,
                "access_level": doc.access_level.value,
                "filename": doc.filename,
                "title": doc.title
            }
            metadatas.append(meta)

            db_chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                org_id=org_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                token_count=chunk.token_count,
                page_number=chunk.page_number,
                vector_id=v_id,
                metadata_json=meta
            )
            db_chunks.append(db_chunk)

        vector_store.upsert_chunks(
            chunk_ids=chunk_ids,
            embeddings=vectors,
            documents=texts,
            metadatas=metadatas
        )

        session.add_all(db_chunks)
        await session.commit()

    # Step 4: Execute & Assert RAG Query 1 (Vacation Policy -> Page 1)
    async with async_session() as session:
        res = await session.execute(select(User).where(User.id == user_id))
        current_user = res.scalar_one()

        retrieved_q1 = await RetrievalService.retrieve_relevant_chunks(
            query="What is the annual paid vacation days allowance?",
            user=current_user,
            db=session,
            top_k=3
        )

        assert len(retrieved_q1) > 0
        assert retrieved_q1[0]["page_number"] == 1
        assert "28 days" in retrieved_q1[0]["content"]

        # Step 5: Execute & Assert RAG Query 2 (Home Office -> Page 2)
        retrieved_q2 = await RetrievalService.retrieve_relevant_chunks(
            query="How much is the quarterly home office reimbursement?",
            user=current_user,
            db=session,
            top_k=3
        )

        assert len(retrieved_q2) > 0
        assert retrieved_q2[0]["page_number"] == 2
        assert "$450" in retrieved_q2[0]["content"]

        # Step 6: Execute & Assert RAG Query 3 (Password Policy -> Page 3)
        retrieved_q3 = await RetrievalService.retrieve_relevant_chunks(
            query="What is the password length requirement for company laptops?",
            user=current_user,
            db=session,
            top_k=3
        )

        assert len(retrieved_q3) > 0
        assert retrieved_q3[0]["page_number"] == 3
        assert "16 characters" in retrieved_q3[0]["content"]
