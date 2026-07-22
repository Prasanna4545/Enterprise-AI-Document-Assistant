from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.embeddings import EmbeddingService
from app.services.vector_store import VectorStoreService
from app.models.models import User, UserRole, AccessLevel, Document, DocumentPermission, DocumentStatus


class RetrievalService:
    @staticmethod
    async def get_user_accessible_document_ids(db: AsyncSession, user: User) -> List[str]:
        """
        Computes all document IDs in user's org that the user has explicit or role-based permission to view.
        """
        if user.role == UserRole.ADMIN:
            stmt = select(Document.id).where(
                Document.org_id == user.org_id,
                Document.status == DocumentStatus.COMPLETED
            )
            res = await db.execute(stmt)
            return [d for d in res.scalars().all()]

        # For non-admin users, collect doc IDs via access_level, ownership, or explicit DocumentPermission
        # 1. Base access level condition
        allowed_access = [AccessLevel.PUBLIC]
        if user.role == UserRole.MANAGER:
            allowed_access.append(AccessLevel.MANAGERS_ONLY)

        base_stmt = select(Document.id).where(
            Document.org_id == user.org_id,
            Document.status == DocumentStatus.COMPLETED,
            (Document.access_level.in_(allowed_access)) | (Document.uploaded_by_user_id == user.id)
        )
        base_res = await db.execute(base_stmt)
        accessible_ids = set(base_res.scalars().all())

        # 2. DocumentPermission condition (granted to user's role or user's ID)
        perm_stmt = select(DocumentPermission.document_id).where(
            DocumentPermission.org_id == user.org_id,
            (DocumentPermission.granted_role == user.role) | (DocumentPermission.granted_user_id == user.id)
        )
        perm_res = await db.execute(perm_stmt)
        for perm_doc_id in perm_res.scalars().all():
            accessible_ids.add(perm_doc_id)

        return list(accessible_ids)

    @staticmethod
    async def retrieve_relevant_chunks(
        query: str,
        user: User,
        db: AsyncSession,
        top_k: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Embeds user query, computes accessible document IDs for user,
        executes vector search filtered at the vector engine level,
        and enriches chunks with document metadata.
        """
        # Step 1: Compute allowed document IDs for requesting user
        allowed_doc_ids = await RetrievalService.get_user_accessible_document_ids(db, user)
        if not allowed_doc_ids:
            return []

        # Step 2: Embed Query
        query_embedding = EmbeddingService.get_embedding(query)

        # Step 3: Vector search in VectorStore (filtered at vector query level)
        vector_store = VectorStoreService()
        raw_results = vector_store.query(
            query_embedding=query_embedding,
            org_id=user.org_id,
            allowed_doc_ids=allowed_doc_ids,
            top_k=top_k
        )

        if not raw_results:
            return []


        # Step 4: Enrich results with document DB titles and filenames
        doc_ids = list(set([r["metadata"].get("document_id") for r in raw_results if r["metadata"].get("document_id")]))
        
        doc_map = {}
        if doc_ids:
            stmt = select(Document).where(Document.id.in_(doc_ids), Document.org_id == user.org_id)
            res = await db.execute(stmt)
            documents = res.scalars().all()
            for doc in documents:
                doc_map[doc.id] = {
                    "title": doc.title,
                    "filename": doc.filename,
                    "file_type": doc.file_type
                }

        enriched_chunks = []
        for r in raw_results:
            d_id = r["metadata"].get("document_id")
            doc_info = doc_map.get(d_id, {"title": "Document", "filename": "file.pdf", "file_type": "pdf"})
            
            page_num = r["metadata"].get("page_number")
            try:
                page_num = int(page_num) if page_num is not None else 1
            except Exception:
                page_num = 1

            enriched_chunks.append({
                "chunk_id": r["chunk_id"],
                "document_id": d_id,
                "title": doc_info["title"],
                "filename": doc_info["filename"],
                "file_type": doc_info["file_type"],
                "page_number": page_num,
                "content": r["content"],
                "distance": r["distance"]
            })

        return enriched_chunks
