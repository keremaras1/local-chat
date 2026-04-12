"""Message endpoints.

POST /api/conversations/{id}/messages
  — persists user message, creates empty assistant placeholder,
    returns both bubbles (user rendered, assistant wired for SSE streaming).

GET /api/conversations/{id}/messages/{mid}/stream
  — SSE endpoint that streams Ollama tokens into the placeholder bubble,
    then persists the full response on completion.
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.auth import require_htmx
from app.db import async_session_maker, get_db
from app.models import Conversation, Message
from app.ollama import chat_stream
from app.queries import (
    DEFAULT_CONVERSATION_TITLE,
    get_conversation_by_id,
    get_messages_for_conversation,
)
from app.templates_env import templates

router = APIRouter()


@router.post(
    "/api/conversations/{conversation_id}/messages",
    response_class=HTMLResponse,
    dependencies=[Depends(require_htmx)],
)
async def send_message(
    request: Request,
    conversation_id: uuid.UUID,
    content: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    conv = await get_conversation_by_id(db, conversation_id)
    if conv is None:
        return HTMLResponse("Conversation not found", status_code=404)

    user_msg = Message(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        role="user",
        content=content.strip(),
    )
    db.add(user_msg)

    assistant_msg = Message(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        role="assistant",
        content="",
        model=conv.model,
    )
    db.add(assistant_msg)

    if conv.title == DEFAULT_CONVERSATION_TITLE:
        conv.title = content.strip()[:60] or DEFAULT_CONVERSATION_TITLE

    # Force updated_at to refresh on every new message, even when title doesn't change.
    conv.updated_at = datetime.now(timezone.utc)

    await db.commit()

    user_html = templates.get_template("partials/message_user.html").render(
        msg=user_msg
    )
    streaming_html = templates.get_template(
        "partials/message_assistant_streaming.html"
    ).render(msg=assistant_msg, conversation_id=str(conversation_id))

    return HTMLResponse(user_html + streaming_html)


@router.get("/api/conversations/{conversation_id}/messages/{message_id}/stream")
async def stream_message(
    request: Request,
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
):
    async def event_generator() -> AsyncGenerator[dict, None]:
        async with async_session_maker() as db:
            conv = await get_conversation_by_id(db, conversation_id)
            if conv is None:
                yield {"event": "error", "data": "Conversation not found"}
                return

            history = await get_messages_for_conversation(
                db, conversation_id, exclude_id=message_id
            )

        messages_payload = [
            {"role": m.role, "content": m.content}
            for m in history
            if m.content
        ]

        accumulated: list[str] = []

        try:
            async for token in chat_stream(
                model=conv.model,
                messages=messages_payload,
                system_prompt=conv.system_prompt,
            ):
                if await request.is_disconnected():
                    break
                accumulated.append(token)
                yield {"event": "token", "data": token}

        except Exception as exc:
            yield {"event": "error", "data": f"Ollama error: {exc}"}
            return

        full_content = "".join(accumulated)

        async with async_session_maker() as db:
            await db.execute(
                update(Message)
                .where(Message.id == message_id)
                .values(content=full_content)
            )
            await db.commit()

        # Render from in-memory data — the template only uses msg.id and msg.content.
        from types import SimpleNamespace
        msg_data = SimpleNamespace(id=message_id, content=full_content)
        rendered = templates.get_template("partials/message_assistant.html").render(
            msg=msg_data
        )
        yield {"event": "done", "data": rendered}

    return EventSourceResponse(event_generator())
