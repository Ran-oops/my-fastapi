import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_get_tasks_requires_auth(client: TestClient):
    """Test that task endpoints require authentication."""
    response = await client.get("/api/v1/tasks")
    assert response.status_code in (401, 403)
