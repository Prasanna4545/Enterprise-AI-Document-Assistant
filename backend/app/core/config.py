import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise AI Document Assistant"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENV: str = "development"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./enterprise_doc_db.db"
    SYNC_DATABASE_URL: str = "sqlite:///./enterprise_doc_db.db"


    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security & Auth
    JWT_SECRET_KEY: str = "super-secret-jwt-key-for-enterprise-doc-assistant-2026-secure-key"
    JWT_REFRESH_SECRET_KEY: str = "super-secret-refresh-key-for-enterprise-doc-assistant-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    # AI APIs
    ANTHROPIC_API_KEY: str = "mock-anthropic-key"
    OPENAI_API_KEY: str = "mock-openai-key"

    # Vector Store & File Storage
    VECTOR_STORE_TYPE: str = "chroma"  # 'chroma' or 'pinecone'
    CHROMA_PERSIST_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_data")
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = "us-east-1"
    PINECONE_INDEX_NAME: str = "enterprise-docs"

    STORAGE_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
