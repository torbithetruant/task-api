from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Task

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/")
async def list_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task))
    tasks = result.scalars().all()
    return [{"id": t.id, "title": t.title, "status": t.status} for t in tasks]


@router.post("/")
async def create_task(title: str, db: AsyncSession = Depends(get_db)):
    task = Task(title=title)
    db.add(task)
    await db.flush() 
    return {"id": task.id, "title": task.title}