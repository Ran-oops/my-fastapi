from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import status

from app.modules.orders.models import OrderStatus


@pytest.mark.asyncio
class TestOrderAPICreate:
    async def test_create_order_success(self, client, user_headers, test_product_for_order):
        with patch("app.modules.orders.service.dispatch"):
            response = await client.post(
                "/api/v1/orders/",
                json={
                    "user_id": 1,
                    "items": [
                        {
                            "product_id": test_product_for_order.id,
                            "quantity": 2,
                            "unit_price": "99.99",
                        }
                    ],
                },
                headers=user_headers,
            )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["total_amount"] == "199.98"

    async def test_create_order_unauthorized(self, client, test_product_for_order):
        response = await client.post(
            "/api/v1/orders/",
            json={
                "user_id": 1,
                "items": [
                    {
                        "product_id": test_product_for_order.id,
                        "quantity": 1,
                        "unit_price": "50.00",
                    }
                ],
            },
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_create_order_invalid_quantity(self, client, user_headers, test_product_for_order):
        response = await client.post(
            "/api/v1/orders/",
            json={
                "user_id": 1,
                "items": [
                    {
                        "product_id": test_product_for_order.id,
                        "quantity": 0,
                        "unit_price": "50.00",
                    }
                ],
            },
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_create_order_invalid_price(self, client, user_headers, test_product_for_order):
        response = await client.post(
            "/api/v1/orders/",
            json={
                "user_id": 1,
                "items": [
                    {
                        "product_id": test_product_for_order.id,
                        "quantity": 1,
                        "unit_price": "-10.00",
                    }
                ],
            },
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
class TestOrderAPIList:
    async def test_list_orders_admin_success(self, client, superuser_headers, test_order):
        response = await client.get("/api/v1/orders/", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "total" in data

    async def test_list_orders_pagination(self, client, superuser_headers):
        response = await client.get("/api/v1/orders/?page=1&page_size=2", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) <= 2

    async def test_list_orders_filter_by_user(self, client, superuser_headers, test_order):
        response = await client.get(f"/api/v1/orders/?user_id={test_order.user_id}", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for order in data["data"]:
            assert order["user_id"] == test_order.user_id

    async def test_list_orders_filter_by_status(self, client, superuser_headers, test_order):
        response = await client.get("/api/v1/orders/?status=PENDING", headers=superuser_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for order in data["data"]:
            assert order["status"].lower() == "pending"

    async def test_list_orders_unauthorized(self, client):
        response = await client.get("/api/v1/orders/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_list_orders_forbidden(self, client, user_headers):
        response = await client.get("/api/v1/orders/", headers=user_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
class TestOrderAPIMyOrders:
    async def test_my_orders_success(self, client, user_headers):
        response = await client.get("/api/v1/orders/my", headers=user_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data

    async def test_my_orders_unauthorized(self, client):
        response = await client.get("/api/v1/orders/my")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestOrderAPIGetById:
    async def test_get_order_by_id_found(self, client, user_headers, test_order):
        response = await client.get(f"/api/v1/orders/{test_order.id}", headers=user_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == test_order.id

    async def test_get_order_by_id_not_found(self, client, user_headers):
        response = await client.get("/api/v1/orders/99999", headers=user_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_order_by_id_unauthorized(self, client, test_order):
        response = await client.get(f"/api/v1/orders/{test_order.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestOrderAPIUpdate:
    async def test_update_order_admin_success(self, client, superuser_headers, test_order):
        response = await client.put(
            f"/api/v1/orders/{test_order.id}",
            json={"status": "CONFIRMED"},
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["status"].lower() == "confirmed"

    async def test_update_order_invalid_transition(self, client, superuser_headers, test_order):
        response = await client.put(
            f"/api/v1/orders/{test_order.id}",
            json={"status": "SHIPPED"},
            headers=superuser_headers,
        )
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

    async def test_update_order_forbidden(self, client, user_headers, test_order):
        response = await client.put(
            f"/api/v1/orders/{test_order.id}",
            json={"status": "CONFIRMED"},
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_update_order_unauthorized(self, client, test_order):
        response = await client.put(
            f"/api/v1/orders/{test_order.id}",
            json={"status": "CONFIRMED"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestOrderAPIDelete:
    async def test_delete_order_admin_success(self, client, superuser_headers, test_order):
        response = await client.delete(f"/api/v1/orders/{test_order.id}", headers=superuser_headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_delete_order_forbidden(self, client, user_headers, test_order):
        response = await client.delete(f"/api/v1/orders/{test_order.id}", headers=user_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_delete_order_unauthorized(self, client, test_order):
        response = await client.delete(f"/api/v1/orders/{test_order.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
