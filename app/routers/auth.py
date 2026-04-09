from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.database import get_db
from app.models import User
from app.schemas import UserRegister
from app.config import settings
from app.auth import (
    verify_password, 
    create_access_token, 
    get_password_hash
)

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = structlog.get_logger()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return JWT token."""
    logger.info("login_attempt", username=form_data.username)
    
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning("login_failed", username=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        logger.warning("login_attempt_inactive_user", username=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    logger.info("login_successful", username=form_data.username, user_id=user.id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):  # Change signature
    """Register a new user with secure password hashing."""
    logger.info("registration_attempt", username=user_data.username)
    
    # Use user_data fields instead of direct args
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )
    
    hashed_password = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    logger.info("user_registered", username=user_data.username, user_id=user.id)
    
    return {
        "id": user.id,
        "username": user.username,
        "message": "User created successfully"
    }