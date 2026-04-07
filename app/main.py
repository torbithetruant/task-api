from contextlib import asynccontextmanager

import structlog
import uuid
from fastapi import FastAPI, Request
from sqlalchemy import text

from app.config import configure_logging, settings
from app.database import engine
from app.routers import tasks

configure_logging()

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_starting", service="task-api", debug=settings.debug)
    
    # Verify DB connection
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("database_connected")
    
    yield
    
    logger.info("application_shutting_down")
    await engine.dispose()


app = FastAPI(lifespan=lifespan, title="Task API", version="0.1.0")
app.include_router(tasks.router)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    
    logger.info(
        "request_started",
        method=request.method,
        path=request.url.path,
        request_id=request_id,
    )
    
    response = await call_next(request)
    
    logger.info(
        "request_completed",
        status_code=response.status_code,
        request_id=request_id,
    )
    return response


@app.get("/health")
async def health_check():
    logger.debug("health_check_called")
    return {"status": "ok"}