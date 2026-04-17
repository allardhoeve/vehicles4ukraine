FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN groupadd -g 1002 vehicles && useradd -u 1002 -g vehicles -m vehicles

WORKDIR /app

# Install dependencies first (cache layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application
COPY db.py search.py web.py config.yaml ./
RUN chown -R vehicles:vehicles /app

# Shared volume for the database
VOLUME /data
ENV V4U_DB_PATH=/data/vehicles.db

USER vehicles
EXPOSE 5001
