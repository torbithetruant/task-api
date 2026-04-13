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

```powershell
docker-compose up --build

docker-compose down
```

### Run migrations

```powershell
# Start just the DB container
docker-compose up db -d

# Generate the migration
docker-compose run --rm migrate alembic revision --autogenerate -m "initial schema with auth and tasks"

# Apply the migration
docker-compose run --rm migrate alembic upgrade head
```

### Delete database

```powershell
# Delete all files in alembic/versions
Remove-Item alembic/versions\*.py

docker-compose down -v
```

## Tests

```powershell
# Register & Login
 $token = Invoke-RestMethod -Method POST -Uri "http://localhost:8000/auth/login" -ContentType "application/x-www-form-urlencoded" -Body "username=bob&password=password123"
 $headers = @{"Authorization" = "Bearer $($token.access_token)"}
```

```powershell
# Create task
 $newTask = Invoke-RestMethod -Method POST -Uri "http://localhost:8000/tasks/" -Headers $headers -ContentType "application/json" -Body '{"title":"Finish Project 1","status":"todo"}'
 $newTask.id
```

```powershell
# Partial Update task (change the status)
# Replace 3 by the value of newTask.id
Invoke-RestMethod -Method PUT -Uri "http://localhost:8000/tasks/3" -Headers $headers -ContentType "application/json" -Body '{"status":"done"}'
```

```powershell
Invoke-RestMethod -Method GET -Uri "http://localhost:8000/tasks" -Headers $headers
```