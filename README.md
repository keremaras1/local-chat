# LocalChat

A self-hosted LLM chat UI that runs entirely on your local network. Built with FastAPI, HTMX, and PostgreSQL. Streams responses token-by-token from any model installed in [Ollama](https://ollama.com).

Designed to run on a Raspberry Pi 5 alongside Pi-hole, with no external dependencies after first boot.

## Features

- Real-time token streaming via SSE
- Persistent conversation history (PostgreSQL)
- Markdown rendering with syntax highlighting
- Model selection per conversation (any model installed in Ollama)
- Single shared password auth — no accounts needed
- Fully offline after `docker compose up` (all JS vendored locally)

## Requirements

- Docker and Docker Compose
- [Ollama](https://ollama.com) installed and running on the host machine
- At least one model pulled in Ollama (e.g. `ollama pull llama3.2:3b`)

## Setup

**1. Clone the repo and create your `.env` file:**

```bash
cp .env.example .env
```

Fill in the required values:

```
APP_SECRET=    # generate with: python3 -c "import secrets; print(secrets.token_hex(32))"
APP_PASSWORD=  # the password used to log in to the UI
DB_PASSWORD=   # password for the Postgres container
```

**2. Start the app:**

```bash
docker compose up -d
```

Visit `http://localhost:8000`.

## Raspberry Pi / Linux deployment

Docker and UFW have a known networking conflict on Linux that prevents containers from reaching the host. Use the Pi-specific override file instead:

```bash
docker compose -f docker-compose.yml -f docker-compose.pi.yml up -d
```

Also set `OLLAMA_HOST=http://localhost:11434` in your `.env` on the Pi.

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `APP_SECRET` | Yes | — | Secret key for signing session cookies (min 32 chars) |
| `APP_PASSWORD` | Yes | — | Shared password to access the UI |
| `DB_PASSWORD` | Yes | — | Postgres container password |
| `OLLAMA_HOST` | No | `http://host.docker.internal:11434` | URL of the Ollama instance |
| `OLLAMA_DEFAULT_MODEL` | No | — | Pre-select a model for new conversations |
| `OLLAMA_TIMEOUT_S` | No | `300` | Max seconds to wait for a response |
| `LOG_LEVEL` | No | `INFO` | Uvicorn log level |

## Development

The `docker-compose.override.yml` (gitignored) enables live reload and mounts the source directory into the container:

```yaml
services:
  app:
    volumes:
      - .:/app
    command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
```

Create this file locally to enable hot reload during development.

## Tech stack

- **FastAPI** + Jinja2 templates
- **HTMX** + SSE for streaming (vendored, no CDN)
- **SQLAlchemy 2.0** async + asyncpg
- **Alembic** for migrations
- **PostgreSQL 16**
- **markdown-it-py** + Pygments for server-side markdown rendering
- **DOMPurify** + marked.js for client-side streaming render
