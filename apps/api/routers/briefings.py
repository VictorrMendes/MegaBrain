from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from core.dependencies import get_briefing_engine
from engines.briefing import BriefingEngine
from schemas.briefing import BriefingRequest, BriefingResponse

router = APIRouter(prefix="/briefings", tags=["briefings"])


@router.post(
    "/{workspace_id}/generate",
    response_model=BriefingResponse,
)
async def generate_briefing(
    workspace_id: UUID,
    body: BriefingRequest = BriefingRequest(),
    engine: BriefingEngine = Depends(get_briefing_engine),
):
    try:
        briefing = await engine.generate(
            workspace_id=workspace_id,
            type=body.type,
            additional_context=body.additional_context,
        )
        return BriefingResponse.from_orm(briefing)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/{workspace_id}",
    response_model=list[BriefingResponse],
)
async def list_briefings(
    workspace_id: UUID,
    limit: int = 10,
    engine: BriefingEngine = Depends(get_briefing_engine),
):
    briefings = await engine.list(workspace_id, limit=limit)
    return [BriefingResponse.from_orm(b) for b in briefings]


@router.get(
    "/{workspace_id}/{briefing_id}",
    response_model=BriefingResponse,
)
async def get_briefing(
    workspace_id: UUID,
    briefing_id: UUID,
    engine: BriefingEngine = Depends(get_briefing_engine),
):
    briefing = await engine.get(briefing_id)
    if briefing is None or briefing.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Briefing not found")
    return BriefingResponse.from_orm(briefing)
