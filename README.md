# Task API

Production-grade FastAPI with PostgreSQL.

## Quick Start

```bash
docker-compose up --build
```

## API

- GET /health - Health check
- POST /tasks/?title={title} - Create task
- GET /tasks/ - List tasks

## Stack

- FastAPI + SQLAlchemy 2.0 (async)
- PostgreSQL 15
- Docker + docker-compose