from contextlib import asynccontextmanager
from datetime import datetime

import structlog
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import configure_logging, settings
from app.database import engine, get_db
from app.routers import tasks, auth
from app.exceptions import BaseAPIException

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    configure_logging()
    logger.info("application_starting", service="task-api", debug=settings.debug)
    
    # Verify DB connection
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("database_connected")
    
    yield
    
    # Shutdown
    logger.info("application_shutting_down")
    await engine.dispose()


app = FastAPI(
    lifespan=lifespan, 
    title="Task API", 
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,  # Disable docs in production
    redoc_url="/redoc" if settings.debug else None
)

# Include routers
app.include_router(tasks.router)
app.include_router(auth.router)

# Exception handlers
@app.exception_handler(BaseAPIException)
async def api_exception_handler(request: Request, exc: BaseAPIException):
    """Handle custom API exceptions."""
    logger.warning(
        "api_exception",
        error_code=exc.detail["error"]["code"],
        message=exc.detail["error"]["message"],
        path=request.url.path
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors without leaking internals."""
    logger.error(
        "database_error",
        error=str(exc),
        path=request.url.path
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "details": {}
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all for unexpected errors."""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        path=request.url.path,
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {}
            }
        }
    )


# Middleware for request logging
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    import uuid
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
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        request_id=request_id,
    )
    return response

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Remove server header
    if "Server" in response.headers:
        del response.headers["Server"]
    
    return response

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check that verifies database connectivity."""
    try:
        result = await db.execute(text("SELECT 1 as is_alive"))
        row = result.fetchone()
        
        if row and row.is_alive == 1:
            logger.debug("health_check_passed")
            return {
                "status": "healthy",
                "service": "task-api",
                "timestamp": datetime.utcnow().isoformat(),
                "checks": {
                    "database": "ok"
                }
            }
        else:
            raise Exception("Database check failed")
            
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "service": "task-api",
                "error": "Database connectivity issue"
            }
        )