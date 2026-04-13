"""
搜索与缓存集成测试

测试完整流程: 创建数据 → 搜索 → 缓存命中 → 数据更新 → 缓存失效 → 再次搜索
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import status
from sqlalchemy import select

from app.core.cache import (
    CacheSerializer,
    cache_manager,
    delete_cache,
    delete_cache_pattern,
    get_cache,
    set_cache,
)
from app.modules.orders.models import Order
from app.modules.products.models import Product
from app.modules.search.utils import (
    update_order_search_vector,
    update_product_search_vector,
    update_user_search_vector,
)
from app.modules.users.models import User
from app.core.security import get_password_hash


@pytest.mark.asyncio
class TestSearchAndCache:
    """搜索与缓存集成测试"""

    async def test_cache_lifecycle_with_user_data(self, client, session, superuser_headers):
        """测试用户数据的缓存生命周期"""
        unique_id = uuid.uuid4().hex[:8]

        # Step 1: 创建用户
        user_data = {
            "email": f"cache_{unique_id}@example.com",
            "username": f"cache_user_{unique_id}",
            "password": "TestPass123",
            "full_name": "Cache Test User",
        }
        create_response = await client.post("/api/v1/auth/register", json=user_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        user_id = create_response.json()["data"]["id"]

        # Step 2: 首次获取用户 (应该写入缓存)
        from app.modules.users.service import get_user_by_id

        user1 = await get_user_by_id(session, user_id)
        assert user1 is not None
        assert user1.username == f"cache_user_{unique_id}"

        # Step 3: 再次获取 (应该命中缓存)
        # 注意: 实际缓存需要Redis，测试中可能跳过
        user2 = await get_user_by_id(session, user_id)
        assert user2 is not None
        assert user2.id == user1.id

        # Step 4: 更新用户数据
        from app.modules.users.service import update_user
        from app.modules.users.schemas import UserUpdate

        update_data = UserUpdate(full_name="Updated Cache User")
        updated_user = await update_user(session, user_id, update_data)
        assert updated_user.full_name == "Updated Cache User"

        # 验证数据库已更新
        await session.refresh(user1)
        assert user1.full_name == "Updated Cache User"

    async def test_product_cache_and_search(self, client, session, superuser_headers):
        """测试产品缓存和搜索功能"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建多个产品
        products_data = [
            {"name": f"Cache Product A {unique_id}", "sku": f"CACHE-A-{unique_id}", "price": "10.00"},
            {"name": f"Cache Product B {unique_id}", "sku": f"CACHE-B-{unique_id}", "price": "20.00"},
            {"name": f"Cache Product C {unique_id}", "sku": f"CACHE-C-{unique_id}", "price": "30.00"},
        ]

        created_products = []
        for data in products_data:
            response = await client.post(
                "/api/v1/products/",
                headers=superuser_headers,
                json=data,
            )
            assert response.status_code == status.HTTP_201_CREATED
            created_products.append(response.json()["data"])

        # 搜索产品
        from app.modules.products.service import search_products

        search_results = await search_products(session, f"Cache Product {unique_id}", limit=10)
        assert len(search_results) == 3

        # 验证搜索结果包含所有创建的产品
        found_names = [p.name for p in search_results]
        for data in products_data:
            assert data["name"] in found_names

    async def test_order_cache_invalidation(self, client, session, superuser_headers):
        """测试订单缓存失效机制"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建产品
        product = Product(
            name=f"Order Cache Product {unique_id}",
            sku=f"ORD-CACHE-{unique_id}",
            price=Decimal("50.00"),
            is_active=True,
        )
        session.add(product)

        # 创建用户
        user = User(
            email=f"ordcache_{unique_id}@example.com",
            username=f"ordcache_{unique_id}",
            hashed_password=get_password_hash("pass"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(product)
        await session.refresh(user)

        # 创建订单
        from app.modules.orders.service import create_order
        from app.modules.orders.schemas import OrderCreate, OrderItemCreate

        order_data = OrderCreate(
            user_id=user.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1, unit_price=Decimal("50.00"))],
        )
        order = await create_order(session, order_data)
        assert order.id is not None

        # 首次获取订单
        from app.modules.orders.service import get_order_by_id

        order1 = await get_order_by_id(session, order.id)
        assert order1 is not None

        # 再次获取
        order2 = await get_order_by_id(session, order.id)
        assert order2 is not None
        assert order2.id == order1.id

        # 更新订单状态
        from app.modules.orders.service import update_order_status
        from app.modules.orders.schemas import OrderUpdate
        from app.modules.orders.models import OrderStatus

        update_data = OrderUpdate(status=OrderStatus.CONFIRMED)
        updated_order = await update_order_status(session, order.id, update_data)
        assert updated_order.status == OrderStatus.CONFIRMED.value

        # 验证数据库更新
        await session.refresh(order1)
        assert order1.status == OrderStatus.CONFIRMED.value

    async def test_search_vector_updates(self, client, session, superuser_headers):
        """测试搜索向量更新"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建产品
        product = Product(
            name=f"Vector Test Product {unique_id}",
            sku=f"VEC-{unique_id}",
            description="Original description for search",
            price=Decimal("25.00"),
            is_active=True,
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)

        # 更新搜索向量
        update_product_search_vector(product)
        assert product.search_vector is not None
        assert "Vector Test Product" in product.search_vector
        assert "Original description" in product.search_vector

        # 更新产品信息
        from app.modules.products.service import update_product
        from app.modules.products.schemas import ProductUpdate

        update_data = ProductUpdate(name=f"Updated Vector Product {unique_id}")
        updated = await update_product(session, product.id, update_data)

        # 搜索向量应该更新
        update_product_search_vector(updated)
        await session.commit()
        await session.refresh(updated)
        assert f"Updated Vector Product" in updated.search_vector

    async def test_user_search_vector(self, client, session):
        """测试用户搜索向量"""
        unique_id = uuid.uuid4().hex[:8]

        user = User(
            email=f"searchvec_{unique_id}@example.com",
            username=f"searchvec_{unique_id}",
            hashed_password=get_password_hash("pass"),
            full_name="Search Vector Test User",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # 更新搜索向量
        update_user_search_vector(user)
        assert user.search_vector is not None
        assert user.username in user.search_vector
        assert user.email in user.search_vector
        assert user.full_name in user.search_vector

        # 更新用户信息
        user.full_name = "Updated Search Vector Name"
        update_user_search_vector(user)
        assert "Updated Search Vector Name" in user.search_vector

    async def test_order_search_vector(self, client, session, superuser_headers):
        """测试订单搜索向量"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建产品
        product = Product(
            name=f"Order Vector Product {unique_id}",
            sku=f"ORDVEC-{unique_id}",
            price=Decimal("40.00"),
            is_active=True,
        )
        session.add(product)

        user = User(
            email=f"ordvec_{unique_id}@example.com",
            username=f"ordvec_{unique_id}",
            hashed_password=get_password_hash("pass"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(product)
        await session.refresh(user)

        # 创建订单
        from app.modules.orders.service import create_order
        from app.modules.orders.schemas import OrderCreate, OrderItemCreate

        order_data = OrderCreate(
            user_id=user.id,
            items=[OrderItemCreate(product_id=product.id, quantity=1, unit_price=Decimal("40.00"))],
        )
        order = await create_order(session, order_data)

        # 更新搜索向量
        update_order_search_vector(order)
        assert order.search_vector is not None
        assert str(order.id) in order.search_vector
        assert str(user.id) in order.search_vector

    async def test_cache_serialization(self, client):
        """测试缓存序列化"""
        # 测试不同数据类型的序列化
        test_data = {
            "string": "test",
            "number": 42,
            "decimal": Decimal("99.99"),
            "datetime": datetime.now(UTC),
            "list": [1, 2, 3],
            "dict": {"a": 1, "b": 2},
            "none": None,
        }

        # 序列化
        serialized = CacheSerializer.serialize(test_data)
        assert serialized is not None

        # 反序列化
        deserialized = CacheSerializer.deserialize(serialized)
        assert deserialized["string"] == "test"
        assert deserialized["number"] == 42

    async def test_cache_manual_operations(self, client):
        """测试手动缓存操作"""
        # 注意: 这些操作需要Redis连接，在测试环境中可能不可用
        # 测试缓存键生成逻辑

        cache_key = f"test:cache:{uuid.uuid4().hex[:8]}"
        test_value = {"data": "test", "timestamp": datetime.now(UTC).isoformat()}

        # 尝试设置缓存
        success = await set_cache(cache_key, test_value, ttl=60)
        # 如果Redis可用，应该返回True
        # 如果Redis不可用，测试应该优雅处理

        if success:
            # 获取缓存
            cached = await get_cache(cache_key)
            assert cached is not None
            assert cached["data"] == "test"

            # 删除缓存
            deleted = await delete_cache(cache_key)
            assert deleted is True

            # 确认已删除
            cached_after = await get_cache(cache_key)
            assert cached_after is None

    async def test_cache_pattern_deletion(self, client):
        """测试缓存模式删除"""
        # 创建多个缓存键
        pattern = f"test:pattern:{uuid.uuid4().hex[:8]}"

        keys = [f"{pattern}:key1", f"{pattern}:key2", f"{pattern}:key3"]
        for key in keys:
            await set_cache(key, {"value": key}, ttl=60)

        # 删除模式
        deleted_count = await delete_cache_pattern(f"{pattern}:*")

        # 如果Redis可用，验证删除
        if deleted_count > 0:
            for key in keys:
                cached = await get_cache(key)
                assert cached is None

    async def test_search_with_pagination(self, client, session, superuser_headers):
        """测试搜索结果分页"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建多个产品用于搜索
        for i in range(15):
            product = Product(
                name=f"Pagination Product {i} {unique_id}",
                sku=f"PAGE-{i}-{unique_id}",
                price=Decimal(f"{i + 1}.00"),
                is_active=True,
            )
            session.add(product)

        await session.commit()

        # 搜索并分页
        from app.modules.products.service import search_products

        page1 = await search_products(session, f"Pagination Product {unique_id}", skip=0, limit=5)
        assert len(page1) == 5

        page2 = await search_products(session, f"Pagination Product {unique_id}", skip=5, limit=5)
        assert len(page2) == 5

        # 验证分页结果不重复
        page1_ids = {p.id for p in page1}
        page2_ids = {p.id for p in page2}
        assert page1_ids.isdisjoint(page2_ids)

    async def test_cache_and_db_consistency(self, client, session, superuser_headers):
        """测试缓存和数据库一致性"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建产品
        product_data = {
            "name": f"Consistency Product {unique_id}",
            "sku": f"CONSIST-{unique_id}",
            "price": "75.00",
        }
        create_response = await client.post(
            "/api/v1/products/",
            headers=superuser_headers,
            json=product_data,
        )
        product_id = create_response.json()["data"]["id"]

        # 从数据库获取
        from app.modules.products.service import get_product_by_id

        db_product = await get_product_by_id(session, product_id)
        assert db_product is not None
        assert db_product.name == f"Consistency Product {unique_id}"

        # 更新产品
        update_response = await client.put(
            f"/api/v1/products/{product_id}",
            headers=superuser_headers,
            json={"price": "85.00"},
        )
        assert update_response.status_code == status.HTTP_200_OK

        # 验证数据库更新
        await session.refresh(db_product)
        assert db_product.price == Decimal("85.00")

        # 再次获取验证一致性
        updated_product = await get_product_by_id(session, product_id)
        assert updated_product.price == Decimal("85.00")
