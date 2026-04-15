"""Full-page routes — renders the complete Jinja layout."""

import asyncio
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Message
from app.queries import get_conversation_by_id, get_conversations, safe_list_models
from app.templates_env import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: AsyncSession = Depends(get_db)):
    conversations, models = await asyncio.gather(
        get_conversations(db),
        safe_list_models(),
    )
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "conversations": conversations,
            "active_conversation": None,
            "messages": [],
            "models": models,
        },
    )


@router.get("/c/{conversation_id}", response_class=HTMLResponse)
async def conversation_page(
    request: Request,
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    is_htmx = bool(request.headers.get("HX-Request"))
    models_task = asyncio.create_task(safe_list_models())

    # Skip sidebar query on HTMX partial requests — conversations list is not used.
    conversations = [] if is_htmx else await get_conversations(db)
    conv = await get_conversation_by_id(db, conversation_id)
    models = await models_task

    if conv is None:
        return RedirectResponse(url="/", status_code=302)

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = list(msg_result.scalars().all())

    ctx = {
        "active_conversation": conv,
        "messages": messages,
        "models": models,
    }

    if is_htmx:
        return templates.TemplateResponse(request, "partials/chat_pane.html", ctx)

    return templates.TemplateResponse(
        request, "index.html", {**ctx, "conversations": conversations}
    )
