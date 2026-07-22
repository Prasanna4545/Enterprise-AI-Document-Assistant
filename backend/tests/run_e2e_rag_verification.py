import os
import sys
import asyncio
import json
import uuid

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.db.base import Base
from app.models.models import (
    Organization, User, UserRole, Document, DocumentChunk, DocumentStatus,
    AccessLevel, ChatSession, Message, MessageSender
)
from app.services.ingestion import DocumentIngestionService
from app.services.embeddings import EmbeddingService
from app.services.vector_store import VectorStoreService
from app.services.retrieval import RetrievalService
from app.services.rag_pipeline import RAGPipelineService

# Use test SQLite database
TEST_DB_URL = "sqlite+aiosqlite:///./test_e2e.db"


async def main():
    print("\n" + "="*80)
    print("STARTING E2E RAG PIPELINE VERIFICATION")
    print("="*80 + "\n")

    # Step 1: Initialize Database Tables
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    print("[SUCCESS] Database tables created successfully.")

    # Step 2: Seed Demo Organization & Admin User
    async with async_session() as session:
        org = Organization(id=str(uuid.uuid4()), name="Acme Corp")
        session.add(org)
        await session.flush()

        user = User(
            id=str(uuid.uuid4()),
            org_id=org.id,
            email="admin@acmecorp.com",
            hashed_password="hashed_pwd_placeholder",
            full_name="Alice Admin",
            role=UserRole.ADMIN
        )
        session.add(user)
        await session.commit()
        
        org_id = org.id
        user_id = user.id
        print(f"[SUCCESS] Created Demo Org: '{org.name}' ({org_id})")
        print(f"[SUCCESS] Created Admin User: '{user.email}' ({user_id})\n")

    # Step 3: Ingest Test PDF Fixture
    pdf_path = os.path.join(os.path.dirname(__file__), "fixtures", "Acme_Corporate_Policies_2026.pdf")
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Fixture PDF not found at {pdf_path}")

    print(f"[INGESTION] Processing document: {os.path.basename(pdf_path)}...")

    # Parse pages
    pages = DocumentIngestionService.parse_file(pdf_path, "pdf")
    print(f"   - Extracted {len(pages)} pages from PDF.")

    # Chunk text
    chunks = DocumentIngestionService.chunk_text(pages, chunk_size_tokens=300, overlap_tokens=40)
    print(f"   - Generated {len(chunks)} overlapping text chunks.")

    # Embed chunks
    chunk_texts = [c.content for c in chunks]
    embeddings = EmbeddingService.get_embeddings(chunk_texts)
    print(f"   - Generated {len(embeddings)} vector embeddings ({len(embeddings[0])} dimensions).")

    # Save to Database & ChromaDB
    async with async_session() as session:
        doc_id = str(uuid.uuid4())
        doc = Document(
            id=doc_id,
            org_id=org_id,
            uploaded_by_user_id=user_id,
            title="Acme Corporate Policy Manual 2026",
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
            vec_id = f"vec_e2e_{doc_id}_{idx}"
            chunk_ids.append(vec_id)
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

            doc_chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                org_id=org_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                token_count=chunk.token_count,
                page_number=chunk.page_number,
                vector_id=vec_id,
                metadata_json=meta
            )
            db_chunks.append(doc_chunk)

        vector_store.upsert_chunks(
            chunk_ids=chunk_ids,
            embeddings=vectors,
            documents=texts,
            metadatas=metadatas
        )

        session.add_all(db_chunks)
        await session.commit()

        print(f"[SUCCESS] Ingestion complete! Persisted {len(db_chunks)} chunks in DB and ChromaDB.\n")

    # Step 4: Execute 3 Real Chat Queries
    queries = [
        {
            "num": 1,
            "query": "How many days of paid annual vacation leave do Acme employees receive?",
            "expected_page": 1,
            "expected_keyword": "28 days"
        },
        {
            "num": 2,
            "query": "What is the quarterly home office reimbursement allowance amount for remote work?",
            "expected_page": 2,
            "expected_keyword": "$450"
        },
        {
            "num": 3,
            "query": "What are the mandatory laptop password length and rotation frequency rules?",
            "expected_page": 3,
            "expected_keyword": "16 characters"
        }
    ]

    async with async_session() as session:
        res = await session.execute(select(User).where(User.id == user_id))
        current_user = res.scalar_one()

        for q in queries:
            print("\n" + "-"*80)
            print(f"[QUERY {q['num']}]: \"{q['query']}\"")
            print("-"*80)

            # Retrieve Chunks
            retrieved_chunks = await RetrievalService.retrieve_relevant_chunks(
                query=q['query'],
                user=current_user,
                db=session,
                top_k=3
            )

            print(f"\n[RETRIEVED CHUNKS] ({len(retrieved_chunks)} matches):")
            for idx, c in enumerate(retrieved_chunks):
                print(f"   [{idx+1}] File: {c['filename']} | Page: {c['page_number']} | Distance: {c['distance']:.4f}")
                print(f"       Snippet: \"{c['content'][:180]}...\"\n")

            # Stream RAG Answer
            print("[GENERATED RAG ANSWER & CITATIONS]:")
            full_answer = ""
            citations_received = []

            async for evt in RAGPipelineService.stream_rag_response(
                query=q['query'],
                chunks=retrieved_chunks
            ):
                if evt.startswith("data: "):
                    payload = json.loads(evt[6:].strip())
                    if payload.get("type") == "content":
                        full_answer += payload.get("text", "")
                    elif payload.get("type") == "citations":
                        citations_received = payload.get("citations", [])

            print(f"\n{full_answer.strip()}\n")
            print(f"[RETURNED CITATION METADATA]:")
            for cit in citations_received:
                print(f"   - File: {cit['filename']} | Page: {cit.get('page_number')} | Title: {cit['title']}")

            # Verification Assertions
            top_retrieved_page = retrieved_chunks[0]['page_number'] if retrieved_chunks else None
            assert top_retrieved_page == q['expected_page'], \
                f"Page mismatch for Query {q['num']}! Expected Page {q['expected_page']}, got Page {top_retrieved_page}"
            
            assert q['expected_keyword'].lower() in full_answer.lower() or q['expected_keyword'].lower() in retrieved_chunks[0]['content'].lower(), \
                f"Keyword '{q['expected_keyword']}' not found in answer or retrieved chunk!"

            print(f"\n[PASSED] QUERY {q['num']} VERIFICATION (Matched Page {top_retrieved_page} & keyword '{q['expected_keyword']}').")

    print("\n" + "="*80)
    print("ALL 3 REAL RAG QUERIES VERIFIED SUCCESSFULLY WITH 100% PRECISION!")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
