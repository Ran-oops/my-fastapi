import uuid

import pytest
from fastapi import status

from tests.conftest import NONEXISTENT_ID


@pytest.mark.asyncio
class TestProductAPICreate:
    async def test_create_product_admin_success(self, client, superuser_headers):
        response = await client.post(
            "/api/v1/products/",
            json={
                "name": "API Test Product",
                "sku": f"API-{uuid.uuid4().hex[:8]}",
                "description": "Created via API",
                "price": "79.99",
                "category": "api-test",
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "API Test Product"

    async def test_create_product_forbidden(self, client, user_headers):
        response = await client.post(
            "/api/v1/products/",
            json={
                "name": "Forbidden",
                "sku": f"FORB-{uuid.uuid4().hex[:8]}",
                "price": "19.99",
            },
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_create_product_unauthorized(self, client):
        response = await client.post(
            "/api/v1/products/",
            json={"name": "Unauthorized", "sku": f"UNAUTH-{uuid.uuid4().hex[:8]}", "price": "19.99"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestProductAPIList:
    async def test_get_products_authenticated_success(self, client, user_headers, test_product):
        response = await client.get("/api/v1/products/", headers=user_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "data" in response.json()
        assert "total" in response.json()

    async def test_get_products_filter_by_category(self, client, user_headers, multiple_products):
        response = await client.get("/api/v1/products/?category=electronics", headers=user_headers)
        assert response.status_code == status.HTTP_200_OK
        for product in response.json()["data"]:
            assert product["category"] == "electronics"

    async def test_get_products_unauthorized(self, client):
        assert (await client.get("/api/v1/products/")).status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestProductAPIGetById:
    async def test_get_product_by_id_found(self, client, user_headers, test_product):
        response = await client.get(f"/api/v1/products/{test_product.id}", headers=user_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["id"] == test_product.id

    async def test_get_product_by_id_not_found(self, client, user_headers):
        assert (
            await client.get(f"/api/v1/products/{NONEXISTENT_ID}", headers=user_headers)
        ).status_code == status.HTTP_404_NOT_FOUND

    async def test_get_product_by_sku_found(self, client, user_headers, test_product):
        response = await client.get(f"/api/v1/products/sku/{test_product.sku}", headers=user_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["sku"] == test_product.sku

    async def test_get_product_by_sku_not_found(self, client, user_headers):
        assert (
            await client.get("/api/v1/products/sku/NONEXISTENT-SKU", headers=user_headers)
        ).status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
class TestProductAPIUpdate:
    async def test_update_product_admin_success(self, client, superuser_headers, test_product):
        response = await client.put(
            f"/api/v1/products/{test_product.id}",
            json={"name": "Updated via API", "price": "199.99"},
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["name"] == "Updated via API"

    async def test_update_product_forbidden(self, client, user_headers, test_product):
        assert (
            await client.put(
                f"/api/v1/products/{test_product.id}",
                json={"name": "Forbidden"},
                headers=user_headers,
            )
        ).status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestProductAPIDelete:
    async def test_delete_product_admin_success(self, client, superuser_headers):
        product_sku = f"DEL-API-{uuid.uuid4().hex[:8]}"
        create_resp = await client.post(
            "/api/v1/products/",
            json={"name": "To Delete", "sku": product_sku, "price": "29.99", "category": "test"},
            headers=superuser_headers,
        )
        product_id = create_resp.json()["data"]["id"]
        assert (
            await client.delete(f"/api/v1/products/{product_id}", headers=superuser_headers)
        ).status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_product_forbidden(self, client, user_headers, test_product):
        assert (
            await client.delete(
                f"/api/v1/products/{test_product.id}",
                headers=user_headers,
            )
        ).status_code == status.HTTP_403_FORBIDDEN
