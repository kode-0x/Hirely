# syntax=docker/dockerfile:1

# Multi-stage build. The builder resolves the locked dependencies into a
# virtual environment with uv; the runtime stage copies only that environment
# and the application code, and runs as a non-root user.

FROM python:3.11-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.2 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /build

# Install only the locked runtime dependencies (no dev group, no project code).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.11-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN useradd --create-home --uid 10001 hirely

COPY --from=builder /opt/venv /opt/venv
COPY src/ ./src/
COPY pages/ ./pages/
COPY app.py ./app.py
COPY .streamlit/ ./.streamlit/
COPY .agents/skills/ ./.agents/skills/

USER hirely

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health').status == 200 else 1)"

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
