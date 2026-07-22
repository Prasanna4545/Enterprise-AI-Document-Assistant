from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.models import User, Organization, UserRole
from app.schemas.schemas import (
    UserSignup, UserLogin, TokenResponse, RefreshTokenRequest, UserResponse
)
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.dependencies import get_current_user
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserSignup, db: AsyncSession = Depends(get_db)):
    """Registers a new Organization and Admin User."""
    # Check if user email already exists
    existing_user = await db.execute(select(User).where(User.email == payload.email))
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User with this email already exists.")

    # Create Organization
    org = Organization(name=payload.organization_name)
    db.add(org)
    await db.flush()

    # Create User as ADMIN for new org
    hashed_pwd = hash_password(payload.password)
    user = User(
        org_id=org.id,
        email=payload.email,
        hashed_password=hashed_pwd,
        full_name=payload.full_name,
        role=UserRole.ADMIN
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Log audit
    await AnalyticsService.log_action(
        db=db,
        org_id=org.id,
        user_id=user.id,
        action="USER_SIGNUP",
        resource_type="USER",
        resource_id=user.id,
        metadata_json={"org_name": org.name, "email": user.email}
    )

    access_token = create_access_token(data={"sub": user.id, "org_id": org.id, "role": user.role.value})
    refresh_token = create_refresh_token(data={"sub": user.id})

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    """Logs in an existing user and returns JWT tokens."""
    result = await db.execute(select(User).where(User.email == payload.email, User.is_active == True))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # Log audit
    await AnalyticsService.log_action(
        db=db,
        org_id=user.org_id,
        user_id=user.id,
        action="USER_LOGIN",
        resource_type="USER",
        resource_id=user.id
    )

    access_token = create_access_token(data={"sub": user.id, "org_id": user.org_id, "role": user.role.value})
    refresh_token = create_refresh_token(data={"sub": user.id})

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Refreshes access token using a valid refresh token."""
    decoded = decode_token(payload.refresh_token, is_refresh=True)
    if not decoded or decoded.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")

    user_id = decoded.get("sub")
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User account no longer active.")

    access_token = create_access_token(data={"sub": user.id, "org_id": user.org_id, "role": user.role.value})
    new_refresh = create_refresh_token(data={"sub": user.id})

    return TokenResponse(access_token=access_token, refresh_token=new_refresh)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Returns details of the currently authenticated user."""
    res = await db.execute(select(Organization.name).where(Organization.id == current_user.org_id))
    org_name = res.scalar_one_or_none()
    
    return UserResponse(
        id=current_user.id,
        org_id=current_user.org_id,
        organization_name=org_name or "Organization",
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )
