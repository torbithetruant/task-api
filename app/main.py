from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine, Base
from app.routers import tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(tasks.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}