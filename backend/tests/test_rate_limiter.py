import os
import sys
import asyncio
import time
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models.models import User, UserRole, Organization
from app.core.security import create_access_token
from app.core.rate_limiter import RateLimiter, _inmemory_sliding_windows
from app.api.chat import router as chat_router

TEST_APP = FastAPI()
TEST_APP.include_router(chat_router, prefix="/api/v1")


@pytest.mark.asyncio
async def test_sliding_window_rate_limiter_and_retry_after():
    """
    Integration Test:
    1. Simulates requests exceeding the defined rate limit for an Employee user.
    2. Asserts HTTP 429 Too Many Requests and presence of 'Retry-After' header.
    3. Confirms Admin user is exempt (unlimited).
    4. Verifies limit resets after window expires.
    """
    # Create test rate limiter with 10s window and limit=3 for test speed
    limiter = RateLimiter(endpoint_name="test_endpoint", custom_limit=3, window_seconds=10)

    # 1. Employee User
    emp_user = User(
        id="user_emp_123",
        org_id="org_test_789",
        email="emp@test.com",
        full_name="Test Employee",
        role=UserRole.EMPLOYEE
    )

    # Dummy request object
    dummy_req = Request(scope={"type": "http", "method": "POST", "path": "/test"})

    # Clear rate limit memory
    _inmemory_sliding_windows.clear()

    # 2. Fire 3 allowed requests
    for i in range(3):
        await limiter(request=dummy_req, current_user=emp_user)

    # 3. Fire 4th request -> Expect HTTP 429 & Retry-After header
    with pytest.raises(HTTPException) as exc_info:
        await limiter(request=dummy_req, current_user=emp_user)

    err = exc_info.value
    assert err.status_code == 429
    assert "Retry-After" in err.headers
    assert int(err.headers["Retry-After"]) >= 1
    assert "Rate limit exceeded" in err.detail

    # 4. Confirm Admin user is EXEMPT (Bypasses rate limiting)
    admin_user = User(
        id="user_admin_456",
        org_id="org_test_789",
        email="admin@test.com",
        full_name="Test Admin",
        role=UserRole.ADMIN
    )
    # Admin can make unlimited calls
    for i in range(10):
        await limiter(request=dummy_req, current_user=admin_user)

    # 5. Clear window timestamps to simulate window passing
    _inmemory_sliding_windows.clear()

    # 6. Verify Employee can request again after window passes
    await limiter(request=dummy_req, current_user=emp_user)

