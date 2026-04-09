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

## Important Commands

### Run/Turn-off application

'''powershell
docker-compose up --build

docker-compose down
'''

### Run migrations

'''powershell
# Start just the DB container
docker-compose up db -d

# Generate the migration
docker-compose run --rm migrate alembic revision --autogenerate -m "initial schema with auth and tasks"

# Apply the migration
docker-compose run --rm migrate alembic upgrade head
'''

### Delete database

'''powershell
# Delete all files in alembic/versions
Remove-Item alembic/versions\*.py

docker-compose down -v
'''