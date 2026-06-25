from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kernel.config import settings
from kernel.events import event_bus
from kernel.logger import get_logger, setup_logging
from core.health import router as health_router
from routers.workspaces import router as workspaces_router
from routers.memories import router as memories_router
from routers.conversations import router as conversations_router

logger = get_logger("khonshu.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("api.starting", env=settings.env)
    await event_bus.connect()
    logger.info("api.ready")
    yield
    await event_bus.disconnect()
    logger.info("api.shutdown")


app = FastAPI(
    title="KHONSHU API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3100", "http://192.168.1.26:3100"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(workspaces_router)
app.include_router(memories_router)
app.include_router(conversations_router)
