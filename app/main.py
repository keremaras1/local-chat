from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.auth import AuthMiddleware
from app.config import settings
from app.markdown import pygments_css, render_markdown
from app import ollama
from app.routers import auth as auth_router
from app.routers import conversations as conversations_router
from app.routers import messages as messages_router
from app.routers import pages as pages_router
from app.templates_env import templates


@asynccontextmanager
async def lifespan(_: FastAPI):
    await ollama.startup()
    Path("static/pygments.css").write_text(pygments_css())
    yield
    await ollama.shutdown()


app = FastAPI(title="LocalChat", lifespan=lifespan)

# Starlette applies middleware LIFO: last added runs first on the request.
# SessionMiddleware must run first to populate request.session before AuthMiddleware checks it.
app.add_middleware(AuthMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.app_secret,
    https_only=False,
    same_site="strict",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router.router)
app.include_router(pages_router.router)
app.include_router(conversations_router.router)
app.include_router(messages_router.router)

templates.env.filters["markdown"] = render_markdown


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
