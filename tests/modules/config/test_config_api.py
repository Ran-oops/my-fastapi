import uuid

import pytest
from fastapi import status

from tests.conftest import NONEXISTENT_ID


@pytest.mark.asyncio
class TestConfigAPIList:
    async def test_get_configs_success(self, client, superuser_headers):
        response = await client.get("/api/v1/config/", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert "page" in data

    async def test_get_configs_unauthorized(self, client):
        response = await client.get("/api/v1/config/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_configs_forbidden(self, client, user_headers):
        response = await client.get("/api/v1/config/", headers=user_headers)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
class TestConfigAPIGetByKey:
    async def test_get_config_by_key_success(self, client, superuser_headers, test_config):
        response = await client.get(f"/api/v1/config/key/{test_config.key}", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["key"] == test_config.key

    async def test_get_config_by_key_not_found(self, client, superuser_headers):
        response = await client.get("/api/v1/config/key/nonexistent.key", headers=superuser_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_config_by_key_unauthorized(self, client):
        response = await client.get("/api/v1/config/key/some.key")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestConfigAPIGetById:
    async def test_get_config_by_id_success(self, client, superuser_headers, test_config):
        response = await client.get(f"/api/v1/config/{test_config.id}", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["id"] == test_config.id

    async def test_get_config_by_id_not_found(self, client, superuser_headers):
        response = await client.get(f"/api/v1/config/{NONEXISTENT_ID}", headers=superuser_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_config_by_id_unauthorized(self, client):
        response = await client.get("/api/v1/config/1")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestConfigAPICreate:
    async def test_create_config_success(self, client, superuser_headers):
        unique_key = f"api.key.{uuid.uuid4().hex[:8]}"
        response = await client.post(
            "/api/v1/config/",
            json={"key": unique_key, "value": "api_test_value", "description": "API test"},
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["data"]["key"] == unique_key
        assert data["data"]["value"] == "api_test_value"

    async def test_create_config_duplicate_key(self, client, superuser_headers, test_config):
        response = await client.post(
            "/api/v1/config/",
            json={"key": test_config.key, "value": "duplicate_value"},
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_create_config_unauthorized(self, client):
        response = await client.post("/api/v1/config/", json={"key": "test", "value": "test"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_create_config_forbidden(self, client, user_headers):
        response = await client.post(
            "/api/v1/config/",
            json={"key": "test.forbidden", "value": "test"},
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_create_config_validation_error(self, client, superuser_headers):
        response = await client.post(
            "/api/v1/config/",
            json={"key": "", "value": "test"},
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
class TestConfigAPIUpdate:
    async def test_update_config_success(self, client, superuser_headers, test_config):
        response = await client.put(
            f"/api/v1/config/{test_config.id}",
            json={"value": "updated_value", "description": "Updated"},
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["value"] == "updated_value"

    async def test_update_config_not_found(self, client, superuser_headers):
        response = await client.put(
            f"/api/v1/config/{NONEXISTENT_ID}",
            json={"value": "updated"},
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_config_unauthorized(self, client, test_config):
        response = await client.put(
            f"/api/v1/config/{test_config.id}",
            json={"value": "updated"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_update_config_forbidden(self, client, user_headers, test_config):
        response = await client.put(
            f"/api/v1/config/{test_config.id}",
            json={"value": "updated"},
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestConfigAPIDelete:
    async def test_delete_config_success(self, client, superuser_headers):
        unique_key = f"delete.key.{uuid.uuid4().hex[:8]}"
        create_response = await client.post(
            "/api/v1/config/",
            json={"key": unique_key, "value": "to_delete"},
            headers=superuser_headers,
        )
        config_id = create_response.json()["data"]["id"]

        response = await client.delete(f"/api/v1/config/{config_id}", headers=superuser_headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_config_not_found(self, client, superuser_headers):
        response = await client.delete(f"/api/v1/config/{NONEXISTENT_ID}", headers=superuser_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_config_unauthorized(self, client, test_config):
        response = await client.delete(f"/api/v1/config/{test_config.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_delete_config_forbidden(self, client, user_headers, test_config):
        response = await client.delete(f"/api/v1/config/{test_config.id}", headers=user_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
