from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.database import get_db
from app.models import User, Task
from app.deps import get_current_active_user

router = APIRouter(prefix="/admin", tags=["admin"])
logger = structlog.get_logger()


async def get_current_admin_user(current_user: User = Depends(get_current_active_user)):
    """Dependency to ensure user is an admin."""
    if not current_user.is_superuser:
        logger.warning("unauthorized_admin_access_attempt", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user


@router.get("/users")
async def list_all_users(
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint to see all registered users."""
    result = await db.execute(select(User))
    users = result.scalars().all()
    
    # Don't return passwords
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "is_active": u.is_active,
            "is_superuser": u.is_superuser
        } for u in users
    ]


@router.get("/stats")
async def get_system_stats(
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint to see system statistics."""
    user_count = await db.execute(select(User).count())
    task_count = await db.execute(select(Task).count())
    
    return {
        "total_users": user_count.scalar(),
        "total_tasks": task_count.scalar()
    }