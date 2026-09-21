FROM python:3-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

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

CMD ["soukk-backend"]
