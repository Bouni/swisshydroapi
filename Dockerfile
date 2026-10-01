FROM ghcr.io/astral-sh/uv:0.12 AS uv

FROM python:3.14-slim-trixie AS builder

COPY --from=uv /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked

COPY app/ /app/app/


FROM python:3.14-slim-trixie

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN mkdir /data

WORKDIR /app
COPY --from=builder /app /app

HEALTHCHECK --interval=1m --timeout=10s --start-period=2m \
  CMD ["python", "-m", "app.check"]

EXPOSE 80
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
