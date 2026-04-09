from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.database import get_db
from app.models import Task, User
from app.schemas import TaskCreate, TaskResponse
from app.exceptions import TaskNotFoundException, ValidationException
from app.deps import get_current_active_user

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = structlog.get_logger()


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    current_user: User = Depends(get_current_active_user),  # Require Login
    db: AsyncSession = Depends(get_db)
):
    """List ONLY the current user's tasks."""
    logger.info("listing_tasks", user_id=current_user.id)
    
    # SECURITY: Filter by owner_id
    result = await db.execute(
        select(Task).where(Task.owner_id == current_user.id)
    )
    tasks = result.scalars().all()
    task_list = [TaskResponse.model_validate(t) for t in tasks]
    logger.info("tasks_retrieved", count=len(task_list), user_id=current_user.id)
    return task_list


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a task ONLY if it belongs to the current user."""
    logger.info("getting_task", task_id=task_id, user_id=current_user.id)
    
    # SECURITY: Check both ID and Owner
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.owner_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        # We return 404 whether it doesn't exist OR it belongs to someone else.
        # This prevents user enumeration (Security Best Practice).
        raise TaskNotFoundException(task_id)
    
    logger.info("task_retrieved", task_id=task_id)
    return task


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a task and assign it to the logged-in user."""
    logger.info("creating_task", title=task_data.title, user_id=current_user.id)
    
    if len(task_data.title) < 3:
        raise ValidationException("Title must be at least 3 characters", field="title")
    
    if len(task_data.title) > 200:
        raise ValidationException("Title too long (max 200 chars)", field="title")
    
    # SECURITY: Force ownership
    task = Task(**task_data.model_dump(), owner_id=current_user.id)
    
    db.add(task)
    await db.commit()
    await db.refresh(task)
    logger.info("task_created", task_id=task.id)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a task ONLY if it belongs to the current user (IDOR Prevention)."""
    logger.info("deleting_task", task_id=task_id, user_id=current_user.id)
    
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.owner_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise TaskNotFoundException(task_id)
    
    await db.delete(task)
    await db.commit()
    logger.info("task_deleted", task_id=task_id)