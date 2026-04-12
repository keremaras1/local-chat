"""Auth flow tests — login, logout, protected routes."""

import pytest


async def test_unauthenticated_root_redirects_to_login(client):
    resp = await client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/login"


async def test_health_is_public(client):
    resp = await client.get("/health")
    assert resp.status_code == 200


async def test_login_page_renders(client):
    resp = await client.get("/login")
    assert resp.status_code == 200
    assert b"Sign in" in resp.content


async def test_wrong_password_returns_401(client):
    resp = await client.post("/login", data={"password": "wrong"})
    assert resp.status_code == 401
    assert b"Incorrect password" in resp.content


async def test_correct_password_redirects_home(client):
    resp = await client.post("/login", data={"password": "testpassword"}, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"


async def test_authenticated_can_access_root(client):
    # Log in first
    await client.post("/login", data={"password": "testpassword"})
    resp = await client.get("/")
    assert resp.status_code == 200


async def test_logout_clears_session(client):
    await client.post("/login", data={"password": "testpassword"})
    await client.post("/logout", follow_redirects=False)
    resp = await client.get("/", follow_redirects=False)
    assert resp.status_code == 302
