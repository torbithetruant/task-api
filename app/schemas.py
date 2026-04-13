from pydantic import BaseModel, ConfigDict
from datetime import datetime


class TaskBase(BaseModel):
    title: str
    description: str | None = None
    status: str = "todo"


class TaskCreate(TaskBase):
    pass


class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime | None = None

class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None

class UserRegister(BaseModel):
    username: str
    email: str
    password: str