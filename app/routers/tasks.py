from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.database import get_db
from app.models import Task
from app.schemas import TaskCreate, TaskResponse
from app.exceptions import TaskNotFoundException, ValidationException

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = structlog.get_logger()


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    logger.info("listing_tasks")
    try:
        result = await db.execute(select(Task))
        tasks = result.scalars().all()
        task_list = [TaskResponse.model_validate(t) for t in tasks]
        logger.info("tasks_retrieved", count=len(task_list))
        return task_list
    except Exception as e:
        logger.error("failed_to_list_tasks", error=str(e))
        raise


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific task by ID."""
    logger.info("getting_task", task_id=task_id)
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        logger.warning("task_not_found", task_id=task_id)
        raise TaskNotFoundException(task_id)
    
    logger.info("task_retrieved", task_id=task_id)
    return task


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task_data: TaskCreate, db: AsyncSession = Depends(get_db)):
    logger.info("creating_task", title=task_data.title)
    
    # Input validation example (security-focused)
    if len(task_data.title) < 3:
        raise ValidationException("Title must be at least 3 characters", field="title")
    
    if len(task_data.title) > 200:
        raise ValidationException("Title too long (max 200 chars)", field="title")
    
    task = Task(**task_data.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    logger.info("task_created", task_id=task.id)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a task."""
    logger.info("deleting_task", task_id=task_id)
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise TaskNotFoundException(task_id)
    
    await db.delete(task)
    await db.commit()
    logger.info("task_deleted", task_id=task_id)