"""Shared database query helpers used by multiple routers."""

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation, Message
from app.ollama import list_models

# Sentinel used both when creating a conversation and when deciding whether
# to auto-rename on the first message. Defined here so both routers stay in sync.
DEFAULT_CONVERSATION_TITLE = "New conversation"


async def get_conversations(db: AsyncSession) -> list[Conversation]:
    result = await db.execute(
        select(Conversation).order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_conversation_by_id(
    db: AsyncSession, conversation_id: uuid.UUID
) -> Conversation | None:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    return result.scalar_one_or_none()


async def get_conversation_or_404(
    db: AsyncSession, conversation_id: uuid.UUID
) -> Conversation:
    conv = await get_conversation_by_id(db, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404)
    return conv


async def get_messages_for_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    exclude_id: uuid.UUID | None = None,
) -> list[Message]:
    q = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    if exclude_id is not None:
        q = q.where(Message.id != exclude_id)
    result = await db.execute(q)
    return list(result.scalars().all())


async def safe_list_models() -> list[str]:
    """Return Ollama model list, or empty list if Ollama is unreachable."""
    try:
        return await list_models()
    except Exception:
        return []
