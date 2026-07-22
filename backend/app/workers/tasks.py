import uuid
import logging
from sqlalchemy import select

from app.workers.celery_app import celery_app
from app.db.session import SyncSessionLocal
from app.models.models import Document, DocumentChunk, DocumentStatus
from app.services.ingestion import DocumentIngestionService
from app.services.embeddings import EmbeddingService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


@celery_app.task(name="process_document_task", bind=True, max_retries=2)
def process_document_task(self, document_id: str):
    """
    Celery background task to parse file, chunk text, generate embeddings,
    and persist vectors in ChromaDB and Postgres metadata tables.
    """
    session = SyncSessionLocal()
    try:
        stmt = select(Document).where(Document.id == document_id)
        document = session.execute(stmt).scalar_one_or_none()

        if not document:
            logger.error(f"Document {document_id} not found.")
            return

        # Update status to PROCESSING
        document.status = DocumentStatus.PROCESSING
        session.commit()

        # Step 1: Parse Document
        pages = DocumentIngestionService.parse_file(document.file_path, document.file_type)

        if not pages:
            document.status = DocumentStatus.FAILED
            document.error_message = "No extractable text content found in document."
            session.commit()
            return

        # Step 2: Chunk Text
        chunks = DocumentIngestionService.chunk_text(pages, chunk_size_tokens=400, overlap_tokens=50)

        if not chunks:
            document.status = DocumentStatus.FAILED
            document.error_message = "Failed to chunk document text."
            session.commit()
            return

        # Step 3: Embed Chunks
        chunk_texts = [c.content for c in chunks]
        embeddings = EmbeddingService.get_embeddings(chunk_texts)

        # Step 4: Vector Store & DB Persistence
        vector_store = VectorStoreService()

        chunk_ids = []
        vectors = []
        texts = []
        metadatas = []

        db_chunks = []

        for idx, chunk in enumerate(chunks):
            v_id = f"vec_{document.id}_{idx}_{uuid.uuid4().hex[:8]}"
            
            chunk_ids.append(v_id)
            vectors.append(embeddings[idx])
            texts.append(chunk.content)
            
            meta = {
                "document_id": document.id,
                "org_id": document.org_id,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number or 1,
                "access_level": document.access_level.value,
                "filename": document.filename,
                "title": document.title
            }
            metadatas.append(meta)

            doc_chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=document.id,
                org_id=document.org_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                token_count=chunk.token_count,
                page_number=chunk.page_number,
                vector_id=v_id,
                metadata_json=meta
            )
            db_chunks.append(doc_chunk)

        # Upsert into ChromaDB
        vector_store.upsert_chunks(
            chunk_ids=chunk_ids,
            embeddings=vectors,
            documents=texts,
            metadatas=metadatas
        )

        # Save to DB
        session.add_all(db_chunks)
        document.chunk_count = len(db_chunks)
        document.status = DocumentStatus.COMPLETED
        document.error_message = None
        session.commit()

        logger.info(f"Successfully processed document {document_id} into {len(db_chunks)} chunks.")

    except Exception as exc:
        session.rollback()
        logger.error(f"Error processing document {document_id}: {exc}")
        try:
            document.status = DocumentStatus.FAILED
            document.error_message = str(exc)
            session.commit()
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=10)
    finally:
        session.close()
