FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1

WORKDIR /soukk-infra

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-cache --no-dev

ENV PATH="/soukk-infra/.venv/bin:$PATH"

RUN useradd --create-home app && chown -R app /soukk-infra
USER app

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os,urllib.request; urllib.request.urlopen(f'http://localhost:{os.getenv(\"PORT\",\"8000\")}/health', timeout=3)"]

CMD ["soukk-backend"]
