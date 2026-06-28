import asyncio
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.integration import ConnectedAccount, AccountStatus
from kernel.runtime import runtime
from kernel.observability.broadcaster import log_broadcaster

router = APIRouter(prefix="/observability", tags=["observability"])

@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    system_health = "healthy"
    
    # Count OAuth errors
    result = await db.execute(
        select(func.count()).select_from(ConnectedAccount).where(ConnectedAccount.status == AccountStatus.error)
    )
    oauth_errors = result.scalar_one()
    
    # Avg API Latency
    execution_stats = runtime.metrics._execution.to_dict()
    avg_latency = execution_stats.get("avg_ms", 0.0)
    
    return {
        "system_health": system_health,
        "oauth_refresh_errors": oauth_errors,
        "avg_api_latency": avg_latency
    }

@router.websocket("/logs/stream")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    q = log_broadcaster.subscribe()
    try:
        while True:
            msg = await q.get()
            await websocket.send_text(msg)
    except WebSocketDisconnect:
        pass
    finally:
        log_broadcaster.unsubscribe(q)
