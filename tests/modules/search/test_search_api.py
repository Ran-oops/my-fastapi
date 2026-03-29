import pytest
from fastapi import status
from httpx import AsyncClient

from tests.conftest import NONEXISTENT_ID


@pytest.mark.asyncio
class TestSearchAPI:
    async def test_search_products(self, client: AsyncClient, user_headers, sample_products):
        response = await client.get(
            "/api/v1/search/",
            params={"q": "Product", "type": "products"},
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "meta" in data
        assert data["meta"]["query"] == "Product"
        assert data["meta"]["search_type"] == "products"

    async def test_search_all_types(self, client: AsyncClient, user_headers, sample_products, sample_users):
        response = await client.get(
            "/api/v1/search/",
            params={"q": "search", "type": "all"},
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "products" in data["data"]
        assert "users" in data["data"]
        assert "orders" in data["data"]

    async def test_search_with_pagination(self, client: AsyncClient, user_headers, sample_products):
        response = await client.get(
            "/api/v1/search/",
            params={"q": "Product", "type": "products", "page": 1, "page_size": 2},
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["meta"]["page"] == 1
        assert data["meta"]["page_size"] == 2

    async def test_search_with_filters(self, client: AsyncClient, user_headers, sample_products):
        response = await client.get(
            "/api/v1/search/",
            params={
                "q": "Product",
                "type": "products",
                "category": "electronics",
            },
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data["data"]["products"]:
            assert item["data"]["category"] == "electronics"

    async def test_search_missing_query(self, client: AsyncClient, user_headers):
        response = await client.get(
            "/api/v1/search/",
            params={"type": "products"},
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_search_invalid_type(self, client: AsyncClient, user_headers):
        response = await client.get(
            "/api/v1/search/",
            params={"q": "test", "type": "invalid"},
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_search_unauthorized(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/search/",
            params={"q": "test"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestSuggestAPI:
    async def test_suggest_success(self, client: AsyncClient, user_headers, sample_products):
        response = await client.get(
            "/api/v1/search/suggest",
            params={"q": "Prod", "type": "products"},
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    async def test_suggest_too_short(self, client: AsyncClient, user_headers):
        response = await client.get(
            "/api/v1/search/suggest",
            params={"q": "P", "type": "products"},
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_suggest_limit(self, client: AsyncClient, user_headers, sample_products):
        response = await client.get(
            "/api/v1/search/suggest",
            params={"q": "Product", "type": "products", "limit": 2},
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) <= 2


@pytest.mark.asyncio
class TestHistoryAPI:
    async def test_get_history_empty(self, client: AsyncClient, user_headers):
        response = await client.get(
            "/api/v1/search/history",
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "total" in data

    async def test_get_history_with_records(self, client: AsyncClient, user_headers, sample_products):
        await client.get(
            "/api/v1/search/",
            params={"q": "Product", "type": "products"},
            headers=user_headers,
        )

        response = await client.get(
            "/api/v1/search/history",
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1

    async def test_delete_history(self, client: AsyncClient, user_headers, sample_products):
        await client.get(
            "/api/v1/search/",
            params={"q": "Product", "type": "products"},
            headers=user_headers,
        )

        history_response = await client.get(
            "/api/v1/search/history",
            headers=user_headers,
        )
        history_data = history_response.json()

        if history_data["data"]:
            history_id = history_data["data"][0]["id"]
            response = await client.delete(
                f"/api/v1/search/history/{history_id}",
                headers=user_headers,
            )
            assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_history_not_found(self, client: AsyncClient, user_headers):
        response = await client.delete(
            f"/api/v1/search/history/{NONEXISTENT_ID}",
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_clear_history(self, client: AsyncClient, user_headers, sample_products):
        await client.get(
            "/api/v1/search/",
            params={"q": "Product", "type": "products"},
            headers=user_headers,
        )

        response = await client.delete(
            "/api/v1/search/history",
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        history_response = await client.get(
            "/api/v1/search/history",
            headers=user_headers,
        )
        history_data = history_response.json()
        assert history_data["total"] == 0

    async def test_history_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/v1/search/history")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
