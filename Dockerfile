FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first (cache layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application
COPY search.py web.py config.yaml ./

# Shared volume for the database
VOLUME /data
ENV V4U_DB_PATH=/data/vehicles.db

EXPOSE 5001
