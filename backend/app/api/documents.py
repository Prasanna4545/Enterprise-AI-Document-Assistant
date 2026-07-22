import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.config import settings
from app.core.dependencies import get_current_user, require_roles
from app.models.models import User, UserRole, Document, DocumentStatus, AccessLevel
from app.schemas.schemas import DocumentResponse, DocumentUpdatePermission, DocumentPermissionResponse, DocumentPermissionGrant

from app.services.analytics_service import AnalyticsService
from app.services.vector_store import VectorStoreService
from app.workers.tasks import process_document_task
from app.core.rate_limiter import RateLimiter

router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt", "md", "xlsx", "xls", "csv"}


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RateLimiter("document_upload"))])
async def upload_document(

    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    access_level: Optional[AccessLevel] = Form(AccessLevel.PUBLIC),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Uploads a document and queues background ingestion."""
    # Check permissions (Only ADMIN or MANAGER can upload)
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Only Admins and Managers can upload documents.")

    filename = file.filename or "uploaded_file.txt"
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file format '.{ext}'. Supported formats: {', '.join(ALLOWED_EXTENSIONS)}")

    # Ensure storage directory exists
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    doc_id = str(uuid.uuid4())
    save_filename = f"{doc_id}_{filename}"
    file_path = os.path.join(settings.STORAGE_DIR, save_filename)

    # Read and save file
    content = await file.read()
    file_size = len(content)
    with open(file_path, "wb") as f:
        f.write(content)

    doc_title = title if title and title.strip() else filename

    document = Document(
        id=doc_id,
        org_id=current_user.org_id,
        uploaded_by_user_id=current_user.id,
        title=doc_title,
        filename=filename,
        file_path=file_path,
        file_type=ext,
        file_size=file_size,
        status=DocumentStatus.PENDING,
        access_level=access_level
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    # Log audit
    await AnalyticsService.log_action(
        db=db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        action="DOCUMENT_UPLOAD",
        resource_type="DOCUMENT",
        resource_id=document.id,
        metadata_json={"filename": filename, "file_size": file_size, "title": doc_title}
    )

    # Queue background processing via Celery (or asyncio fallback if Celery/Redis is unvailable)
    try:
        process_document_task.delay(document.id)
    except Exception:
        # Fallback to FastAPI background task if Celery broker is not running locally
        background_tasks.add_task(process_document_task, document.id)

    return document


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists all documents in the user's organization accessible to their permissions."""
    from app.services.retrieval import RetrievalService
    accessible_doc_ids = await RetrievalService.get_user_accessible_document_ids(db, current_user)
    
    if not accessible_doc_ids:
        return []

    stmt = select(Document).where(
        Document.id.in_(accessible_doc_ids),
        Document.org_id == current_user.org_id
    ).order_by(Document.created_at.desc())
    
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves document metadata by ID."""
    stmt = select(Document).where(Document.id == document_id, Document.org_id == current_user.org_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deletes a document, its DB chunks, vector embeddings, and underlying file."""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Only Admins and Managers can delete documents.")

    stmt = select(Document).where(Document.id == document_id, Document.org_id == current_user.org_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Delete vectors from ChromaDB
    vector_store = VectorStoreService()
    vector_store.delete_document_chunks(doc.id, doc.org_id)

    # Delete underlying file if exists
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass

    # Log audit
    await AnalyticsService.log_action(
        db=db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        action="DOCUMENT_DELETE",
        resource_type="DOCUMENT",
        resource_id=doc.id,
        metadata_json={"title": doc.title, "filename": doc.filename}
    )

    await db.delete(doc)
    await db.commit()


@router.post("/{document_id}/permissions", response_model=DocumentPermissionResponse)
async def update_document_permissions(
    document_id: str,
    payload: DocumentPermissionGrant,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db)
):
    """Sets role and user permission grants for a document."""
    from app.models.models import DocumentPermission
    from app.schemas.schemas import DocumentPermissionDetail
    
    stmt = select(Document).where(Document.id == document_id, Document.org_id == current_user.org_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Update document access level
    doc.access_level = payload.access_level

    # Delete existing granular permissions
    del_stmt = select(DocumentPermission).where(DocumentPermission.document_id == doc.id)
    existing_perms = await db.execute(del_stmt)
    for p in existing_perms.scalars().all():
        await db.delete(p)

    new_perms = []
    # Add role grants
    if payload.granted_roles:
        for r in payload.granted_roles:
            perm = DocumentPermission(
                document_id=doc.id,
                org_id=current_user.org_id,
                granted_role=r
            )
            db.add(perm)
            new_perms.append(perm)

    # Add user grants
    if payload.granted_user_ids:
        for u_id in payload.granted_user_ids:
            perm = DocumentPermission(
                document_id=doc.id,
                org_id=current_user.org_id,
                granted_user_id=u_id
            )
            db.add(perm)
            new_perms.append(perm)

    await db.commit()

    # Log audit
    await AnalyticsService.log_action(
        db=db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        action="UPDATE_DOCUMENT_PERMISSIONS",
        resource_type="DOCUMENT",
        resource_id=doc.id,
        metadata_json={
            "access_level": payload.access_level.value,
            "granted_roles": [r.value for r in payload.granted_roles] if payload.granted_roles else [],
            "granted_user_ids": payload.granted_user_ids or []
        }
    )

    # Fetch user emails for response detail
    user_map = {}
    if payload.granted_user_ids:
        u_stmt = select(User).where(User.id.in_(payload.granted_user_ids))
        u_res = await db.execute(u_stmt)
        for u in u_res.scalars().all():
            user_map[u.id] = {"email": u.email, "name": u.full_name}

    details = []
    for p in new_perms:
        u_info = user_map.get(p.granted_user_id, {}) if p.granted_user_id else {}
        details.append(DocumentPermissionDetail(
            id=p.id,
            granted_role=p.granted_role,
            granted_user_id=p.granted_user_id,
            user_email=u_info.get("email"),
            user_name=u_info.get("name")
        ))

    return DocumentPermissionResponse(
        document_id=doc.id,
        access_level=doc.access_level,
        permissions=details
    )


@router.get("/{document_id}/permissions", response_model=DocumentPermissionResponse)
async def get_document_permissions(
    document_id: str,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves current permissions for a document."""
    from app.models.models import DocumentPermission
    from app.schemas.schemas import DocumentPermissionDetail

    stmt = select(Document).where(Document.id == document_id, Document.org_id == current_user.org_id)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    perm_stmt = select(DocumentPermission).where(DocumentPermission.document_id == doc.id)
    perm_res = await db.execute(perm_stmt)
    perms = perm_res.scalars().all()

    user_ids = [p.granted_user_id for p in perms if p.granted_user_id]
    user_map = {}
    if user_ids:
        u_stmt = select(User).where(User.id.in_(user_ids))
        u_res = await db.execute(u_stmt)
        for u in u_res.scalars().all():
            user_map[u.id] = {"email": u.email, "name": u.full_name}

    details = []
    for p in perms:
        u_info = user_map.get(p.granted_user_id, {}) if p.granted_user_id else {}
        details.append(DocumentPermissionDetail(
            id=p.id,
            granted_role=p.granted_role,
            granted_user_id=p.granted_user_id,
            user_email=u_info.get("email"),
            user_name=u_info.get("name")
        ))

    return DocumentPermissionResponse(
        document_id=doc.id,
        access_level=doc.access_level,
        permissions=details
    )

