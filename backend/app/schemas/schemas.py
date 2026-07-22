from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, EmailStr, Field

from app.models.models import UserRole, DocumentStatus, AccessLevel, MessageSender


# --- Auth & User Schemas ---
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)


class OrganizationResponse(BaseModel):
    id: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserSignup(BaseModel):
    organization_name: str = Field(..., min_length=2, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserCreateAdmin(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.EMPLOYEE


class UserResponse(BaseModel):
    id: str
    org_id: str
    organization_name: Optional[str] = None
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Document Schemas ---
class DocumentResponse(BaseModel):
    id: str
    org_id: str
    uploaded_by_user_id: Optional[str]
    title: str
    filename: str
    file_type: str
    file_size: int
    status: DocumentStatus
    error_message: Optional[str] = None
    chunk_count: int
    access_level: AccessLevel
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentUpdatePermission(BaseModel):
    access_level: AccessLevel


class DocumentPermissionGrant(BaseModel):
    access_level: AccessLevel = AccessLevel.PUBLIC
    granted_roles: Optional[List[UserRole]] = []
    granted_user_ids: Optional[List[str]] = []


class DocumentPermissionDetail(BaseModel):
    id: str
    granted_role: Optional[UserRole] = None
    granted_user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None


class DocumentPermissionResponse(BaseModel):
    document_id: str
    access_level: AccessLevel
    permissions: List[DocumentPermissionDetail]



# --- Chat & RAG Schemas ---
class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Chat"


class ChatSessionResponse(BaseModel):
    id: str
    org_id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


from app.models.models import UserRole, DocumentStatus, AccessLevel, MessageSender, FeedbackRating


class CitationInfo(BaseModel):
    chunk_id: Optional[str] = None
    document_id: str
    filename: str
    title: str
    page_number: Optional[int] = None
    snippet: str


class MessageResponse(BaseModel):
    id: str
    session_id: str
    sender: MessageSender
    content: str
    citations: Optional[List[CitationInfo]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageFeedbackRequest(BaseModel):
    rating: FeedbackRating


class MessageFeedbackResponse(BaseModel):
    id: str
    message_id: str
    user_id: str
    rating: FeedbackRating
    retrieved_chunk_ids: Optional[List[Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NegativeFeedbackDebugItem(BaseModel):
    feedback_id: str
    message_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    user_query: str
    assistant_answer: str
    rating: FeedbackRating
    retrieved_chunks: List[Dict[str, Any]]
    timestamp: datetime



class RAGQueryRequest(BaseModel):
    session_id: str
    query: str = Field(..., min_length=1)


# --- Analytics & Audit Schemas ---
class AuditLogResponse(BaseModel):
    id: str
    org_id: str
    user_id: Optional[str]
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str]
    metadata_json: Optional[Dict[str, Any]]
    timestamp: datetime

    class Config:
        from_attributes = True


class DocUsageMetric(BaseModel):
    document_id: str
    title: str
    filename: str
    reference_count: int


class AnalyticsSummaryResponse(BaseModel):
    total_documents: int
    total_chunks: int
    total_users: int
    total_queries: int
    doc_usage: List[DocUsageMetric]
    queries_last_7_days: Dict[str, int]
