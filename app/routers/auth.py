from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.auth import SESSION_KEY, check_login
from app.templates_env import templates

router = APIRouter()


@router.get("/login")
async def login_page(request: Request):
    if request.session.get(SESSION_KEY):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
async def login_submit(request: Request, password: str = Form(...)):
    if await check_login(request, password):
        request.session[SESSION_KEY] = True
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": "Incorrect password."},
        status_code=401,
    )


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)
