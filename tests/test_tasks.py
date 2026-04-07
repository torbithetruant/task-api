import pytest


@pytest.mark.asyncio
async def test_create_task(client):
    response = await client.post("/tasks/", json={"title": "Test task"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test task"
    assert data["status"] == "todo"


@pytest.mark.asyncio
async def test_list_tasks_empty(client):
    response = await client.get("/tasks/")
    assert response.status_code == 200
    data = response.json()
    assert data == []


@pytest.mark.asyncio
async def test_list_tasks_with_data(client):
    await client.post("/tasks/", json={"title": "Task 1"})
    response = await client.get("/tasks/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Task 1"