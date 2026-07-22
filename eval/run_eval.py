import os
import sys
import asyncio
import time
import uuid
from typing import List, Dict, Any

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

from app.models.models import Base, Organization, User, UserRole, Document, DocumentStatus, DocumentChunk, AccessLevel
from app.services.vector_store import VectorStoreService
from app.services.embeddings import EmbeddingService
from app.services.retrieval import RetrievalService
from app.services.rag_pipeline import RAGPipelineService

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# 16 Benchmark Labeled Test Pairs
EVAL_DATASET = [
    {
        "id": 1,
        "query": "How many days per week can employees work remotely?",
        "expected_page": 1,
        "expected_keyword": "3"
    },
    {
        "id": 2,
        "query": "What are the mandatory core working hours for remote employees?",
        "expected_page": 1,
        "expected_keyword": "10"
    },
    {
        "id": 3,
        "query": "What is the annual home office setup equipment stipend?",
        "expected_page": 1,
        "expected_keyword": "500"
    },
    {
        "id": 4,
        "query": "How many annual PTO days do full-time employees receive?",
        "expected_page": 2,
        "expected_keyword": "20"
    },
    {
        "id": 5,
        "query": "How many paid sick leave days are provided per calendar year?",
        "expected_page": 2,
        "expected_keyword": "10"
    },
    {
        "id": 6,
        "query": "How many weeks of fully paid parental leave are offered?",
        "expected_page": 2,
        "expected_keyword": "12"
    },
    {
        "id": 7,
        "query": "What is the primary healthcare insurance plan offered?",
        "expected_page": 3,
        "expected_keyword": "BlueCross"
    },
    {
        "id": 8,
        "query": "What is the annual company Health Savings Account HSA match?",
        "expected_page": 3,
        "expected_keyword": "1000"
    },
    {
        "id": 9,
        "query": "Which dental insurance network provider is covered?",
        "expected_page": 3,
        "expected_keyword": "Delta"
    },
    {
        "id": 10,
        "query": "What is the maximum company 401k retirement matching percentage?",
        "expected_page": 4,
        "expected_keyword": "4"
    },
    {
        "id": 11,
        "query": "What is the vesting schedule duration for employee equity stock options?",
        "expected_page": 4,
        "expected_keyword": "4-year"
    },
    {
        "id": 12,
        "query": "What is the cliff period requirement for equity option vesting?",
        "expected_page": 4,
        "expected_keyword": "1-year"
    },
    {
        "id": 13,
        "query": "What is the daily per diem allowance limit for business travel meals?",
        "expected_page": 5,
        "expected_keyword": "75"
    },
    {
        "id": 14,
        "query": "How many days in advance must business travel flights be booked?",
        "expected_page": 5,
        "expected_keyword": "14"
    },
    {
        "id": 15,
        "query": "What is the dollar threshold requiring itemized receipts for travel expenses?",
        "expected_page": 5,
        "expected_keyword": "25"
    },
    {
        "id": 16,
        "query": "Is Multi-Factor Authentication MFA mandatory for company systems?",
        "expected_page": 6,
        "expected_keyword": "MFA"
    }
]

# Page Content Mock Data simulating Acme Corporate Policies document
POLICY_PAGES = {
    1: "SECTION 1: REMOTE WORK POLICY. Employees are allowed up to 3 remote days per week. Core mandatory working hours are 10 AM to 4 PM EST. All remote employees receive a $500 annual home office setup equipment stipend.",
    2: "SECTION 2: TIME OFF AND LEAVE POLICIES. Full-time employees receive 20 days of paid annual PTO per calendar year. In addition, 10 paid sick leave days are granted annually. Primary caregivers receive 12 weeks of fully paid parental leave.",
    3: "SECTION 3: HEALTHCARE AND DENTAL BENEFITS. Comprehensive health coverage is provided via BlueCross PPO. The company provides a $1000 annual Health Savings Account HSA match. Dental coverage is provided by Delta Dental.",
    4: "SECTION 4: RETIREMENT AND EQUITY. The company offers a 401(k) plan with a 4% maximum dollar-for-dollar match. Equity stock option grants follow a 4-year vesting schedule with a 1-year cliff period requirement.",
    5: "SECTION 5: TRAVEL AND EXPENSE REIMBURSEMENT. Daily per diem allowance for business travel meals is $75. Flights must be booked at least 14 days in advance. Itemized receipts are mandatory for any expense exceeding $25.",
    6: "SECTION 6: INFORMATION SECURITY AND COMPLIANCE. Multi-Factor Authentication MFA is mandatory across all internal corporate systems. All employee laptops must adhere to SOC2 encryption and clear desk policies."
}


async def main():
    print("Starting RAG Evaluation Benchmark Execution...")
    start_time = time.time()

    # 1. Initialize SQLite in-memory DB and VectorStore
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    org_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    vector_store = VectorStoreService()


    chunk_ids = []
    documents = []
    metadatas = []
    embeddings = []

    # 2. Seed document and chunks
    async with async_session() as session:
        org = Organization(id=org_id, name="Acme Eval Corp")
        user = User(id=user_id, org_id=org_id, email="eval@acme.com", full_name="Eval User", hashed_password="hashedpassword", role=UserRole.ADMIN)

        doc = Document(
            id=doc_id,
            org_id=org_id,
            uploaded_by_user_id=user_id,
            title="Acme Corporate Policies 2026",
            filename="Acme_Corporate_Policies_2026.pdf",
            file_path="/tmp/Acme_Corporate_Policies_2026.pdf",
            file_type="pdf",
            file_size=10240,
            status=DocumentStatus.COMPLETED,
            chunk_count=len(POLICY_PAGES),
            access_level=AccessLevel.PUBLIC
        )
        session.add_all([org, user, doc])

        for page_num, text in POLICY_PAGES.items():
            vec_id = f"vec_eval_p{page_num}_{doc_id}"
            chunk_ids.append(vec_id)
            documents.append(text)
            meta = {
                "document_id": doc_id,
                "org_id": org_id,
                "page_number": page_num,
                "access_level": "PUBLIC",
                "title": doc.title,
                "filename": doc.filename
            }
            metadatas.append(meta)

            db_chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=doc_id,
                org_id=org_id,
                chunk_index=page_num - 1,
                content=text,
                token_count=50,
                page_number=page_num,
                vector_id=vec_id,
                metadata_json=meta
            )
            session.add(db_chunk)

        embeddings = EmbeddingService.get_embeddings(documents)
        await session.commit()


        # Upsert chunks into ChromaDB vector store
        vector_store.upsert_chunks(
            chunk_ids=chunk_ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

    # 3. Execute benchmark evaluation across all dataset items
    eval_results = []
    precision_hits = 0
    correctness_hits = 0
    top_k = 3

    rag_pipeline = RAGPipelineService()

    async with async_session() as session:
        user_obj = (await session.execute(select(User).where(User.id == user_id))).scalar_one()

        for item in EVAL_DATASET:
            q_id = item["id"]
            query = item["query"]
            exp_page = item["expected_page"]
            exp_kw = item["expected_keyword"]

            # Step A: Retrieve Top-K Chunks
            retrieved_chunks = await RetrievalService.retrieve_relevant_chunks(
                query=query,
                user=user_obj,
                db=session,
                top_k=top_k
            )


            retrieved_pages = [c.get("page_number") for c in retrieved_chunks if c.get("page_number")]
            precision_match = exp_page in retrieved_pages
            if precision_match:
                precision_hits += 1

            # Step B: Generate Answer via RAG Pipeline
            generated_answer = ""
            async for sse_chunk in rag_pipeline.stream_rag_response(query=query, chunks=retrieved_chunks):
                if sse_chunk.startswith("data: "):
                    import json
                    try:
                        p_data = json.loads(sse_chunk[6:].strip())
                        if p_data.get("type") == "content":
                            generated_answer += p_data.get("text", "")
                    except Exception:
                        pass

            # Step C: Check Answer Correctness
            correctness_match = exp_kw.lower() in generated_answer.lower()
            if correctness_match:
                correctness_hits += 1

            eval_results.append({
                "id": q_id,
                "query": query,
                "expected_page": exp_page,
                "retrieved_pages": ", ".join(map(str, retrieved_pages)),
                "precision_match": precision_match,
                "expected_keyword": exp_kw,
                "generated_answer": generated_answer,
                "correctness_match": correctness_match
            })

    total_queries = len(EVAL_DATASET)
    precision_score = (precision_hits / total_queries) * 100
    correctness_score = (correctness_hits / total_queries) * 100
    elapsed_time = round(time.time() - start_time, 2)

    # 4. Generate Markdown Evaluation Report
    report_md = f"""# RAG Evaluation Benchmark Report

- **Date Executed**: {time.strftime('%Y-%m-%d %H:%M:%S')}
- **Total Queries Evaluated**: {total_queries}
- **Top-K Window**: {top_k}
- **Total Execution Time**: {elapsed_time}s

## Executive Performance Summary

| Metric | Score | Target Standard | Status |
| :--- | :--- | :--- | :--- |
| **Retrieval Precision@{top_k}** | **{precision_score:.1f}%** ({precision_hits}/{total_queries}) | ≥ 85.0% | {"✅ PASS" if precision_score >= 85 else "⚠️ NEEDS IMPROVEMENT"} |
| **Answer Correctness** | **{correctness_score:.1f}%** ({correctness_hits}/{total_queries}) | ≥ 85.0% | {"✅ PASS" if correctness_score >= 85 else "⚠️ NEEDS IMPROVEMENT"} |

---

## Detailed Per-Query Results Table

| ID | Query Question | Expected Page | Retrieved Pages | Precision Match? | Expected Keyword | Answer Match? |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
"""

    for r in eval_results:
        p_badge = "✅ PASS" if r["precision_match"] else "❌ FAIL"
        c_badge = "✅ PASS" if r["correctness_match"] else "❌ FAIL"
        report_md += f"| {r['id']} | {r['query']} | Page {r['expected_page']} | {r['retrieved_pages']} | {p_badge} | `{r['expected_keyword']}` | {c_badge} |\n"

    report_md += f"""

---

## Generated Answer Quality Breakdown

"""
    for r in eval_results:
        c_badge = "✅ PASS" if r["correctness_match"] else "❌ FAIL"
        report_md += f"### Query {r['id']}: {r['query']}\n"
        report_md += f"- **Expected Page**: Page {r['expected_page']}\n"
        report_md += f"- **Expected Key Fact**: `{r['expected_keyword']}`\n"
        report_md += f"- **Generated Answer**: \"{r['generated_answer']}\"\n"
        report_md += f"- **Result Status**: {c_badge}\n\n"

    # Write report to eval/eval_report.md
    os.makedirs(os.path.dirname(__file__), exist_ok=True)
    report_path = os.path.join(os.path.dirname(__file__), "eval_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"[SUCCESS] Evaluation complete! Report saved to {report_path}")
    print(f"Retrieval Precision@{top_k}: {precision_score:.1f}% | Answer Correctness: {correctness_score:.1f}%")

if __name__ == "__main__":
    asyncio.run(main())
