import pytest
from app.core.config import Settings


def test_settings_database_url_validators():
    """
    Verifies automatic conversion of Railway & cloud Postgres URLs to asyncpg driver
    in Settings.DATABASE_URL and psycopg2 in Settings.SYNC_DATABASE_URL,
    while leaving local SQLite URLs untouched.
    """
    # 1. Plain postgres:// -> postgresql+asyncpg:// for async
    settings_1 = Settings(
        DATABASE_URL="postgres://user:password@railway.app:5432/railway_db",
        SYNC_DATABASE_URL="postgres://user:password@railway.app:5432/railway_db"
    )
    assert settings_1.DATABASE_URL == "postgresql+asyncpg://user:password@railway.app:5432/railway_db"
    assert settings_1.SYNC_DATABASE_URL == "postgresql+psycopg2://user:password@railway.app:5432/railway_db"

    # 2. Plain postgresql:// -> postgresql+asyncpg:// for async
    settings_2 = Settings(
        DATABASE_URL="postgresql://user:password@railway.app:5432/railway_db",
        SYNC_DATABASE_URL="postgresql://user:password@railway.app:5432/railway_db"
    )
    assert settings_2.DATABASE_URL == "postgresql+asyncpg://user:password@railway.app:5432/railway_db"
    assert settings_2.SYNC_DATABASE_URL == "postgresql+psycopg2://user:password@railway.app:5432/railway_db"

    # 3. Already specifies driver -> Unmodified
    settings_3 = Settings(
        DATABASE_URL="postgresql+asyncpg://user:password@host:5432/db",
        SYNC_DATABASE_URL="postgresql+psycopg2://user:password@host:5432/db"
    )
    assert settings_3.DATABASE_URL == "postgresql+asyncpg://user:password@host:5432/db"
    assert settings_3.SYNC_DATABASE_URL == "postgresql+psycopg2://user:password@host:5432/db"

    # 4. SQLite local URLs -> Unmodified
    settings_4 = Settings(
        DATABASE_URL="sqlite+aiosqlite:///./test.db",
        SYNC_DATABASE_URL="sqlite:///./test.db"
    )
    assert settings_4.DATABASE_URL == "sqlite+aiosqlite:///./test.db"
    assert settings_4.SYNC_DATABASE_URL == "sqlite:///./test.db"
