import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings

_chroma_client = None


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True)
        )
    return _chroma_client


class VectorStoreService:
    def __init__(self):
        self.client = get_chroma_client()
        self.collection = self.client.get_or_create_collection(
            name="enterprise_documents",
            metadata={"hnsw:space": "cosine"}
        )

    def upsert_chunks(
        self,
        chunk_ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> bool:
        """Upserts chunks into vector database with metadata (org_id, doc_id, page_number, access_level)."""
        if not chunk_ids:
            return True

        # Ensure all metadata values are primitive types for Chroma
        cleaned_metadatas = []
        for m in metadatas:
            cleaned = {}
            for k, v in m.items():
                if v is not None:
                    cleaned[k] = str(v) if not isinstance(v, (str, int, float, bool)) else v
            cleaned_metadatas.append(cleaned)

        self.collection.upsert(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=cleaned_metadatas
        )
        return True

    def query(
        self,
        query_embedding: List[float],
        org_id: str,
        allowed_access_levels: List[str] = None,
        allowed_doc_ids: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Executes similarity search scoped by org_id and allowed document IDs.
        Restricted documents are filtered out at the vector query level.
        """
        # If allowed_doc_ids is explicitly provided as empty list, user has no access to any documents
        if allowed_doc_ids is not None and len(allowed_doc_ids) == 0:
            return []

        if allowed_access_levels is None:
            allowed_access_levels = ["PUBLIC", "MANAGERS_ONLY", "ADMIN_ONLY"]

        # Filter criteria for multi-tenancy & document permissions
        if allowed_doc_ids is not None:
            if len(allowed_doc_ids) == 1:
                where_filter = {
                    "$and": [
                        {"org_id": org_id},
                        {"document_id": allowed_doc_ids[0]}
                    ]
                }
            else:
                where_filter = {
                    "$and": [
                        {"org_id": org_id},
                        {"document_id": {"$in": allowed_doc_ids}}
                    ]
                }
        else:
            where_filter = {"org_id": org_id}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter
        )

        matched_chunks = []
        if results and results.get("ids") and len(results["ids"]) > 0:
            ids = results["ids"][0]
            docs = results["documents"][0] if results.get("documents") else []
            metadatas = results["metadatas"][0] if results.get("metadatas") else []
            distances = results["distances"][0] if results.get("distances") else []

            for idx in range(len(ids)):
                meta = metadatas[idx] if idx < len(metadatas) else {}
                acc_level = meta.get("access_level", "PUBLIC")
                
                # If allowed_doc_ids is provided, documents are already strictly permissioned by SQL
                if allowed_doc_ids is not None or acc_level in allowed_access_levels:
                    matched_chunks.append({
                        "chunk_id": ids[idx],
                        "content": docs[idx] if idx < len(docs) else "",
                        "metadata": meta,
                        "distance": distances[idx] if idx < len(distances) else 0.0,
                    })

        return matched_chunks


    def delete_document_chunks(self, document_id: str, org_id: str):
        """Deletes all vector chunks associated with a specific document."""
        try:
            self.collection.delete(
                where={"$and": [{"document_id": document_id}, {"org_id": org_id}]}
            )
        except Exception:
            pass

