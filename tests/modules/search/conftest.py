import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest_asyncio

from app.core.security import get_password_hash
from app.modules.orders import service as order_service
from app.modules.orders.schemas import OrderCreate, OrderItemCreate
from app.modules.products import service as product_service
from app.modules.products.schemas import ProductCreate
from app.modules.users.models import User
from tests.helpers import unique_id
from tests.conftest import TEST_PASSWORD


@pytest_asyncio.fixture
async def sample_products(session):
    products = []
    for i in range(5):
        product_in = ProductCreate(
            name=f"Search Product {i}",
            sku=f"SEARCH-{unique_id()}-{i}",
            description=f"Test product for search {i}",
            price=Decimal(f"{(i + 1) * 20}.00"),
            category="electronics" if i % 2 == 0 else "clothing",
        )
        products.append(await product_service.create_product(session, product_in))
    return products


@pytest_asyncio.fixture
async def sample_users(session):
    users = []
    for i in range(3):
        uid = unique_id()
        user = User(
            email=f"searchuser_{uid}_{i}@example.com",
            username=f"searchuser_{uid}_{i}",
            hashed_password=get_password_hash(TEST_PASSWORD),
            full_name=f"Search User {i}",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        users.append(user)
    return users


@pytest_asyncio.fixture
async def sample_order(session, test_user, sample_products):
    with patch("app.modules.orders.service.dispatch"):
        order_in = OrderCreate(
            user_id=test_user.id,
            items=[
                OrderItemCreate(
                    product_id=sample_products[0].id,
                    quantity=2,
                    unit_price=sample_products[0].price,
                )
            ],
        )
        return await order_service.create_order(session, order_in)
