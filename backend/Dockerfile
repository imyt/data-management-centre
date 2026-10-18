# One image for the API and the worker (ADR 0004). Build from the repository root:
#   docker build -f backend/Dockerfile -t dmc-backend .
# The command picks the process: uvicorn (default), dmc-worker, or dmc-migrate upgrade.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /srv/backend

# Dependencies first, so code changes don't reinstall them.
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY backend/app ./app
COPY backend/migrations ./migrations
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Reported by GET /api/v1/meta; the build sets it to the git SHA.
ARG DMC_COMMIT=
ENV DMC_COMMIT=$DMC_COMMIT

RUN useradd --system --uid 10001 dmc
USER dmc

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
