FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml ./

# Install all dependencies including dev
RUN uv pip install --system -e ".[dev]" || uv pip install --system -e .

COPY app/ ./app/
COPY tests/ ./tests/
COPY alembic/ ./alembic/

EXPOSE 8000