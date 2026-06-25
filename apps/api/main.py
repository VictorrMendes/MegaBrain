from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import kernel.plugins  # noqa: F401 — registers all plugins on import
from core.database import AsyncSessionLocal
from core.dependencies import (
    get_llm_provider,
    get_memory_engine,
    get_plugin_engine,
)
from core.health import router as health_router
from kernel.agents import (
    MemoryExtractorWorker,
    SummarizerWorker,
    TaskExtractorWorker,
)
from kernel.config import settings
from kernel.events import event_bus
from kernel.logger import get_logger, setup_logging
from routers.conversations import router as conversations_router
from routers.documents import router as documents_router
from routers.memories import router as memories_router
from routers.plugins import router as plugins_router
from routers.workspaces import router as workspaces_router

logger = get_logger("khonshu.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("api.starting", env=settings.env)
    await event_bus.connect()

    memory_worker = MemoryExtractorWorker(
        memory_engine=get_memory_engine(),
        llm_provider=get_llm_provider(),
    )
    task_worker = TaskExtractorWorker(
        memory_engine=get_memory_engine(),
        llm_provider=get_llm_provider(),
        plugin_engine=get_plugin_engine(),
    )
    summarizer_worker = SummarizerWorker(
        memory_engine=get_memory_engine(),
        llm_provider=get_llm_provider(),
        session_factory=AsyncSessionLocal,
    )

    event_bus.subscribe("khonshu.messages", memory_worker)
    event_bus.subscribe("khonshu.messages", task_worker)
    event_bus.subscribe("khonshu.messages", summarizer_worker)

    logger.info(
        "api.ready",
        workers=["memory_extractor", "task_extractor", "summarizer"],
    )
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
app.include_router(documents_router)
app.include_router(plugins_router)
