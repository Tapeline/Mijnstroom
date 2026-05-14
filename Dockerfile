# syntax=docker/dockerfile:1
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src

RUN uv sync --no-dev

ENV PATH="/opt/venv/bin:${PATH}" \
    MIJNSTROOM_DATA_DIR=/data

VOLUME ["/data"]
EXPOSE 8000

CMD ["python", "-m", "mijnstroom.bootstrap", "web"]
