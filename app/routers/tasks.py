from fastapi import APIRouter, Depends, Query, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import structlog
import json

from app.database import get_db
from app.models import Task, User
from app.schemas import TaskCreate, TaskResponse, TaskUpdate
from app.exceptions import TaskNotFoundException, ValidationException
from app.deps import get_current_active_user
from app.cache import redis_client

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = structlog.get_logger()


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Max records to return"),
    current_user: User = Depends(get_current_active_user),  # Require Login
    db: AsyncSession = Depends(get_db)
):
    """List ONLY the current user's tasks."""
    logger.info("listing_tasks", user_id=current_user.id, skip=skip, limit=limit)
    
    # SECURITY & PERF: Filter by owner_id + Pagination
    result = await db.execute(
        select(Task)
        .where(Task.owner_id == current_user.id)
        .order_by(Task.created_at.desc()) # Newest first
        .limit(limit)
        .offset(skip)
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
    db: AsyncSession = Depends(get_db),
    idempotency_key: str = Header(None, alias="Idempotency-Key")
):
    """Create a task and assign it to the logged-in user."""
    logger.info("creating_task", title=task_data.title, user_id=current_user.id)

    # IDEMPOTENCY CHECK
    if idempotency_key:
        cache_key = f"idempotency:{current_user.id}:{idempotency_key}"
        cached_result = await redis_client.get(cache_key)
        
        if cached_result:
            logger.info("idempotency_hit", key=idempotency_key, user_id=current_user.id)
            # Return the cached result instead of creating a duplicate
            return TaskResponse.model_validate_json(cached_result)
    
    if len(task_data.title) < 3:
        raise ValidationException("Title must be at least 3 characters", field="title")
    
    if len(task_data.title) > 200:
        raise ValidationException("Title too long (max 200 chars)", field="title")
    
    # SECURITY: Force ownership
    task = Task(**task_data.model_dump(), owner_id=current_user.id)
    
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # FIX: Convert SQLAlchemy model to Pydantic model
    response_obj = TaskResponse.model_validate(task)

    # CACHE THE RESULT for Idempotency (24 hours)
    if idempotency_key:
        cache_key = f"idempotency:{current_user.id}:{idempotency_key}"
        await redis_client.set(
            cache_key, 
            response_obj.model_dump_json(), 
            ex=86400 # 24 hours
        )

    logger.info("task_created", task_id=task.id)

    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,  # Use the new schema
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a task. Only the owner can update their own tasks."""
    logger.info("updating_task", task_id=task_id, user_id=current_user.id)
    
    # 1. Fetch task (Security: Verify Ownership)
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.owner_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise TaskNotFoundException(task_id)
    
    # 2. Apply updates (exclude_unset allows partial updates)
    update_data = task_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(task, field, value)
    
    # 3. Save
    await db.commit()
    await db.refresh(task)
    
    logger.info("task_updated", task_id=task_id)
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