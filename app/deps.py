from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from app.database import get_db
from app.models import User
from app.auth import decode_token
import structlog

logger = structlog.get_logger()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Decode JWT token and return current user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token)
        if payload is None:
            raise credentials_exception
            
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        
        if username is None or user_id is None:
            raise credentials_exception
            
    except JWTError:
        logger.warning("invalid_token_attempt")
        raise credentials_exception
    
    # Fetch user from DB to ensure they still exist and are active
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        logger.warning("user_not_found_in_db", user_id=user_id)
        raise credentials_exception
        
    if not user.is_active:
        logger.warning("inactive_user_attempt", user_id=user_id)
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Additional check to ensure user is active (redundant safety)."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user