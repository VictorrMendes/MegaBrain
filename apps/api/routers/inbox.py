from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from core.dependencies import get_inbox_engine
from engines.inbox import InboxEngine
from models.inbox import InboxItemStatus, InboxItemType
from schemas.inbox import (
    InboxItemResponse,
    ProcessResultResponse,
    SubmitInboxRequest,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/inbox",
    tags=["inbox"],
)


@router.post("", response_model=InboxItemResponse, status_code=201)
async def submit_item(
    workspace_id: UUID,
    body: SubmitInboxRequest,
    engine: InboxEngine = Depends(get_inbox_engine),
):
    item = await engine.submit(
        workspace_id=workspace_id,
        raw_content=body.raw_content,
        item_type=body.type,
        title=body.title,
        source=body.source,
        metadata=body.metadata,
        process_now=body.process_now,
    )
    return _to_response(item)


@router.get("", response_model=list[InboxItemResponse])
async def list_items(
    workspace_id: UUID,
    status: InboxItemStatus | None = None,
    type: InboxItemType | None = None,
    limit: int = 50,
    offset: int = 0,
    engine: InboxEngine = Depends(get_inbox_engine),
):
    items = await engine.list_items(
        workspace_id=workspace_id,
        status=status,
        item_type=type,
        limit=limit,
        offset=offset,
    )
    return [_to_response(i) for i in items]


@router.get("/{item_id}", response_model=InboxItemResponse)
async def get_item(
    workspace_id: UUID,
    item_id: UUID,
    engine: InboxEngine = Depends(get_inbox_engine),
):
    try:
        return _to_response(await engine.get_item(item_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{item_id}/process", response_model=ProcessResultResponse)
async def process_item(
    workspace_id: UUID,
    item_id: UUID,
    engine: InboxEngine = Depends(get_inbox_engine),
):
    try:
        item = await engine.process(item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ProcessResultResponse(
        item_id=item.id,
        status=item.status,
        mission_id=item.mission_id,
        knowledge_extracted=item.knowledge_extracted,
        routing_notes=item.routing_notes,
    )


@router.post("/{item_id}/dismiss", response_model=InboxItemResponse)
async def dismiss_item(
    workspace_id: UUID,
    item_id: UUID,
    engine: InboxEngine = Depends(get_inbox_engine),
):
    try:
        return _to_response(await engine.dismiss(item_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


def _to_response(item) -> InboxItemResponse:
    return InboxItemResponse(
        id=item.id,
        workspace_id=item.workspace_id,
        type=item.type,
        status=item.status,
        raw_content=item.raw_content,
        title=item.title,
        source=item.source,
        metadata=item.metadata_,
        mission_id=item.mission_id,
        knowledge_extracted=item.knowledge_extracted,
        routing_notes=item.routing_notes,
        created_at=item.created_at,
        processed_at=item.processed_at,
    )
