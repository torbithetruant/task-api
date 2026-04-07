from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.database import get_db
from app.models import Task
from app.schemas import TaskCreate, TaskResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = structlog.get_logger()


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    logger.info("listing_tasks")
    result = await db.execute(select(Task))
    tasks = result.scalars().all()
    # Force evaluation before session closes
    task_list = [TaskResponse.model_validate(t) for t in tasks]
    logger.info("tasks_retrieved", count=len(task_list))
    return task_list


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task_data: TaskCreate, db: AsyncSession = Depends(get_db)):
    logger.info("creating_task", title=task_data.title)
    task = Task(**task_data.model_dump())
    db.add(task)
    await db.commit()  # Explicit commit
    await db.refresh(task)
    logger.info("task_created", task_id=task.id)
    return task