from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.settings import settings
from app.db.init_db import init_db
from app.services.automation_worker import AutomationWorker


automation_worker = AutomationWorker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle.

    Startup:
        - Initialize the database.
        - Start the automation worker.

    Shutdown:
        - Stop the automation worker cleanly.
    """

    init_db()

    automation_worker.start()

    yield

    automation_worker.stop()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered cryptocurrency trading platform",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    api_router,
    prefix="/api/v1",
)


@app.get(
    "/",
    tags=["Home"],
)
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "status": "running",
        "version": settings.APP_VERSION,
    }