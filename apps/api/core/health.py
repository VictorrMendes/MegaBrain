from fastapi import APIRouter
from sqlalchemy import text
import httpx
import redis.asyncio as aioredis

from core.config import settings
from core.database import engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    status = {"api": "ok", "postgres": "error", "redis": "error", "ollama": "error"}

    # PostgreSQL
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        status["postgres"] = "ok"
    except Exception as e:
        status["postgres"] = str(e)

    # Redis
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        status["redis"] = "ok"
    except Exception as e:
        status["redis"] = str(e)

    # Ollama
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                status["ollama"] = "ok"
    except Exception as e:
        status["ollama"] = str(e)

    overall = "ok" if all(v == "ok" for v in status.values()) else "degraded"
    return {"status": overall, "services": status}
