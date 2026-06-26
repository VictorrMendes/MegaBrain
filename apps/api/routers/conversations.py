from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.dependencies import get_context_builder, get_llm_provider
from kernel.context import ContextBuilder
from kernel.events import event_bus
from kernel.providers.base import ChatMessage, LLMProvider
from models.conversation import Conversation, Message, MessageRole
from schemas.conversation import (
    ChatResponse,
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/conversations",
    tags=["conversations"],
)


# ── SSE helper ──────────────────────────────────────────────────────────────


def _sse(event: str, **data) -> str:
    """Format a Server-Sent Event with a typed event field."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ── CRUD ────────────────────────────────────────────────────────────────────


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    workspace_id: UUID,
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
):
    conv = Conversation(workspace_id=workspace_id, title=data.title)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.workspace_id == workspace_id)
        .order_by(Conversation.updated_at.desc())
    )
    return result.scalars().all()


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
async def get_messages(
    workspace_id: UUID,
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    conv = await db.get(Conversation, conversation_id)
    if conv is None or conv.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return result.scalars().all()


@router.post("/{conversation_id}/messages", response_model=ChatResponse)
async def send_message(
    workspace_id: UUID,
    conversation_id: UUID,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
    ctx_builder: ContextBuilder = Depends(get_context_builder),
):
    conv = await db.get(Conversation, conversation_id)
    if conv is None or conv.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    built = await ctx_builder.build(
        workspace_id=workspace_id,
        user_message=data.content,
    )

    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .limit(20)
    )
    history = list(history_result.scalars())

    messages = [ChatMessage(role="system", content=built.system_prompt)]
    for msg in history:
        messages.append(ChatMessage(role=msg.role.value, content=msg.content))
    messages.append(ChatMessage(role="user", content=data.content))

    result = await llm.chat(messages)

    user_msg = Message(
        conversation_id=conversation_id,
        role=MessageRole.user,
        content=data.content,
    )
    assistant_msg = Message(
        conversation_id=conversation_id,
        role=MessageRole.assistant,
        content=result.content,
    )
    db.add(user_msg)
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(user_msg)
    await db.refresh(assistant_msg)

    return ChatResponse(
        user_message=MessageResponse.model_validate(user_msg),
        assistant_message=MessageResponse.model_validate(assistant_msg),
    )


@router.post("/{conversation_id}/messages/stream")
async def send_message_stream(
    workspace_id: UUID,
    conversation_id: UUID,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
    ctx_builder: ContextBuilder = Depends(get_context_builder),
):
    """Streaming conversation endpoint with typed SSE events.

    Event sequence:
        thinking          — pipeline started
        reading_memory    — memory + knowledge retrieval done (count fields)
        text              — LLM text chunk (content field)
        done              — response complete, messages persisted
        error             — unrecoverable failure (message field)
    """
    conv = await db.get(Conversation, conversation_id)
    if conv is None or conv.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    async def event_stream():
        yield _sse("thinking")

        # ── Build context ────────────────────────────────────────────────
        try:
            built = await ctx_builder.build(
                workspace_id=workspace_id,
                user_message=data.content,
            )
        except Exception as exc:
            yield _sse("error", message=str(exc))
            return

        yield _sse(
            "reading_memory",
            memory=built.memory_count,
            knowledge=built.knowledge_count,
            chunks=built.chunk_count,
        )

        # ── Assemble message list ────────────────────────────────────────
        history_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .limit(20)
        )
        history = list(history_result.scalars())

        messages = [ChatMessage(role="system", content=built.system_prompt)]
        for msg in history:
            messages.append(
                ChatMessage(role=msg.role.value, content=msg.content)
            )
        messages.append(ChatMessage(role="user", content=data.content))

        # ── Stream LLM response ──────────────────────────────────────────
        full_response: list[str] = []
        try:
            async for chunk in llm.chat_stream(messages):
                full_response.append(chunk)
                yield _sse("text", content=chunk)
        except Exception as exc:
            yield _sse("error", message=str(exc))
            return

        response_text = "".join(full_response)

        # ── Persist messages ─────────────────────────────────────────────
        user_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.user,
            content=data.content,
        )
        assistant_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.assistant,
            content=response_text,
        )
        async with db.begin_nested():
            db.add(user_msg)
            db.add(assistant_msg)
        await db.commit()

        count_result = await db.execute(
            select(func.count()).where(
                Message.conversation_id == conversation_id
            )
        )
        msg_count = count_result.scalar_one()

        # ── Publish to workers (memory extractor, summarizer, etc.) ─────
        try:
            await event_bus.publish(
                "khonshu.messages",
                {
                    "type": "message.completed",
                    "workspace_id": str(workspace_id),
                    "conversation_id": str(conversation_id),
                    "user_message": data.content,
                    "assistant_message": response_text,
                    "message_count": msg_count,
                },
            )
        except RuntimeError:
            pass

        yield _sse("done")

    return StreamingResponse(
        event_stream(), media_type="text/event-stream"
    )
