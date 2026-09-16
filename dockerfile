FROM python:3-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /soukk-infra

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache --no-install-project

COPY . .

EXPOSE 8000

CMD ["uv", "run", "soukk-backend"]
