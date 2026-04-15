"""Conversation management API endpoints (HTMX-driven)."""

import uuid

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_htmx
from app.db import get_db
from app.models import Conversation
from app.queries import (
    DEFAULT_CONVERSATION_TITLE,
    get_conversation_or_404,
    safe_list_models,
)
from app.templates_env import templates

router = APIRouter(prefix="/api/conversations")


@router.post("", response_class=HTMLResponse, dependencies=[Depends(require_htmx)])
async def create_conversation(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    models = await safe_list_models()
    conv = Conversation(
        id=uuid.uuid4(),
        title=DEFAULT_CONVERSATION_TITLE,
        model=models[0] if models else "",
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)

    sidebar_item = templates.get_template(
        "partials/conversation_list_item.html"
    ).render(request=request, conv=conv, active_conversation=conv)

    chat_pane_html = templates.get_template("partials/chat_pane.html").render(
        request=request,
        active_conversation=conv,
        messages=[],
        models=models,
    )
    oob_chat_area = (
        f'<main class="chat-main" id="chat-area" hx-swap-oob="outerHTML">'
        f"{chat_pane_html}"
        f"</main>"
    )

    response = HTMLResponse(sidebar_item + oob_chat_area)
    response.headers["HX-Push-Url"] = f"/c/{conv.id}"
    return response


@router.delete("/{conversation_id}", response_class=Response, dependencies=[Depends(require_htmx)])
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        delete(Conversation).where(Conversation.id == conversation_id)
    )
    await db.commit()
    return Response(status_code=200)


@router.patch("/{conversation_id}/model", response_class=HTMLResponse, dependencies=[Depends(require_htmx)])
async def change_model(
    request: Request,
    conversation_id: uuid.UUID,
    model: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    models = await safe_list_models()
    if model not in models:
        return Response(status_code=422)

    conv = await get_conversation_or_404(db, conversation_id)
    conv.model = model
    await db.commit()

    return templates.TemplateResponse(
        request, "partials/model_form.html", {"conv": conv, "models": models}
    )


@router.patch("/{conversation_id}/title", response_class=HTMLResponse, dependencies=[Depends(require_htmx)])
async def rename_conversation(
    request: Request,
    conversation_id: uuid.UUID,
    title: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    conv = await get_conversation_or_404(db, conversation_id)
    conv.title = title.strip()[:200] or conv.title
    await db.commit()
    await db.refresh(conv)

    return templates.TemplateResponse(
        request,
        "partials/conversation_list_item.html",
        {"conv": conv, "active_conversation": conv},
    )
