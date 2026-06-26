import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import kernel.plugins  # noqa: F401 — registers all plugins on import
from core.database import AsyncSessionLocal
from core.health import router as health_router
from kernel.agents import (
    MemoryExtractorWorker,
    SummarizerWorker,
    TaskExtractorWorker,
)
from kernel.config import settings
from kernel.events import event_bus
from kernel.logger import get_logger, setup_logging
from kernel.runtime import runtime
from routers.artifacts import router as artifacts_router
from routers.conversations import router as conversations_router
from routers.dashboard import router as dashboard_router
from routers.documents import router as documents_router
from routers.inbox import router as inbox_router
from routers.knowledge import router as knowledge_router
from routers.memories import router as memories_router
from routers.missions import router as missions_router
from routers.obsidian import router as obsidian_router
from routers.plugins import router as plugins_router
from routers.runtime import router as runtime_router
from routers.scheduler import router as scheduler_router
from routers.search import router as search_router
from routers.workspaces import router as workspaces_router

logger = get_logger("khonshu.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("api.starting", env=settings.env)
    await event_bus.connect()

    runtime.start()
    app.state.runtime = runtime

    memory_worker = MemoryExtractorWorker(
        memory_engine=runtime.memory,
        llm_provider=runtime.llm,
    )
    task_worker = TaskExtractorWorker(
        memory_engine=runtime.memory,
        llm_provider=runtime.llm,
        plugin_engine=runtime.plugin,
    )
    summarizer_worker = SummarizerWorker(
        memory_engine=runtime.memory,
        llm_provider=runtime.llm,
        session_factory=AsyncSessionLocal,
    )

    event_bus.subscribe("khonshu.messages", memory_worker)
    event_bus.subscribe("khonshu.messages", task_worker)
    event_bus.subscribe("khonshu.messages", summarizer_worker)

    # Inicia o tick loop do Scheduler em background
    scheduler = runtime.scheduler

    async def _scheduler_tick_loop() -> None:
        while True:
            try:
                await scheduler.tick()
            except Exception as exc:
                logger.warning("scheduler.tick_error", error=str(exc))
            await asyncio.sleep(60)

    tick_task = asyncio.create_task(_scheduler_tick_loop())

    logger.info(
        "api.ready",
        workers=[
            "memory_extractor",
            "task_extractor",
            "summarizer",
            "scheduler_tick",
        ],
    )
    yield

    tick_task.cancel()
    try:
        await tick_task
    except asyncio.CancelledError:
        pass

    await event_bus.disconnect()
    logger.info("api.shutdown")


app = FastAPI(
    title="KHONSHU API",
    version="0.1.0",
    lifespan=lifespan,
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3100",
        "http://192.168.1.26:3100",
        "https://khonshu.vmserver.app.br",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(runtime_router)
app.include_router(workspaces_router)
app.include_router(memories_router)
app.include_router(conversations_router)
app.include_router(documents_router)
app.include_router(plugins_router)
app.include_router(missions_router)
app.include_router(scheduler_router)
app.include_router(inbox_router)
app.include_router(obsidian_router)
app.include_router(knowledge_router)
app.include_router(artifacts_router)
app.include_router(dashboard_router)
app.include_router(search_router)
