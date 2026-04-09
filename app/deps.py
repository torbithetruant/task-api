from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from app.database import get_db
from app.models import User
from app.auth import decode_token
from app.cache import get_cached_user, cache_user
import structlog

logger = structlog.get_logger()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token)
        if payload is None:
            raise credentials_exception
            
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # 1. Try Cache
    cached_data = await get_cached_user(user_id)
    if cached_data:
        # Reconstruct user object from cache (simplified)
        # In production, you'd need a robust way to map dict back to ORM or just cache necessary fields
        # For now, let's just log the cache hit and proceed to DB to ensure ORM consistency
        logger.info("cache_hit", user_id=user_id)
    
    # 2. Fetch from DB (Cache-Aside Pattern)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # 3. Update Cache
    await cache_user(user_id, {
        "id": user.id, 
        "username": user.username, 
        "email": user.email
    })
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Additional check to ensure user is active (redundant safety)."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user