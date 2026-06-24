FROM python:3.12-slim

WORKDIR /app

# uv para instalar dependências
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml .
RUN uv sync --frozen --no-dev

COPY . .

# Aplicar migrations antes de subir
RUN uv run alembic upgrade head || true

EXPOSE 8100

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8100"]
