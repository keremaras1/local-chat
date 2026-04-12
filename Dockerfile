FROM python:3.12-slim

WORKDIR /app

# asyncpg needs gcc to compile
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (separate layer — changes less often than app code)
COPY pyproject.toml .
RUN pip install --no-cache-dir ".[dev]"

# Copy application code
COPY alembic.ini .
COPY alembic/ ./alembic/
COPY app/ ./app/
COPY static/ ./static/

EXPOSE 8000
