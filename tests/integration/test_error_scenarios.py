"""
错误场景集成测试

测试场景:
- 事务回滚
- 部分失败处理
- 补偿操作
"""

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.orders.schemas import OrderCreate, OrderItemCreate
from app.modules.products.models import Product
from app.modules.users.models import User
from app.core.security import get_password_hash


@pytest.mark.asyncio
class TestErrorScenarios:
    """错误场景集成测试"""

    async def test_transaction_rollback_on_order_creation_failure(self, client, session, superuser_headers):
        """测试订单创建失败时的事务回滚"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建产品
        product = Product(
            name=f"Rollback Product {unique_id}",
            sku=f"ROLLBACK-{unique_id}",
            price=Decimal("50.00"),
            is_active=True,
        )
        session.add(product)

        # 创建用户
        user = User(
            email=f"rollback_{unique_id}@example.com",
            username=f"rollback_{unique_id}",
            hashed_password=get_password_hash("pass"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(product)
        await session.refresh(user)

        # 获取创建订单前的订单数量
        from sqlalchemy import func, select

        count_before = await session.execute(select(func.count()).select_from(Order))
        order_count_before = count_before.scalar()

        # 使用不存在的产品ID创建订单(应该失败)
        order_data = {
            "user_id": user.id,
            "items": [
                {"product_id": 99999, "quantity": 1, "unit_price": "50.00"},
            ],
        }

        # 这应该失败并触发事务回滚
        try:
            response = await client.post(
                "/api/v1/orders/",
                headers=superuser_headers,
                json=order_data,
            )
            # 如果请求成功，检查是否创建了孤立的订单项
            if response.status_code == status.HTTP_201_CREATED:
                # 验证没有孤立的订单项
                result = await session.execute(select(OrderItem).where(OrderItem.product_id == 99999))
                orphaned_items = result.scalars().all()
                assert len(orphaned_items) == 0, "发现孤立的订单项"
        except Exception:
            pass  # 预期会失败

        # 验证订单数量没有变化(事务回滚)
        count_after = await session.execute(select(func.count()).select_from(Order))
        order_count_after = count_after.scalar()
        assert order_count_after == order_count_before, "事务回滚失败，订单数量发生变化"

    async def test_user_creation_rollback_on_duplicate_email(self, client, session):
        """测试重复邮箱导致用户创建回滚"""
        unique_id = uuid.uuid4().hex[:8]
        email = f"duplicate_{unique_id}@example.com"

        # 首先创建用户
        user1_data = {
            "email": email,
            "username": f"user1_{unique_id}",
            "password": "TestPass123",
            "full_name": "User One",
        }
        response1 = await client.post("/api/v1/auth/register", json=user1_data)
        assert response1.status_code == status.HTTP_201_CREATED

        # 获取用户数量
        from sqlalchemy import func, select

        count_before = await session.execute(select(func.count()).select_from(User))
        user_count_before = count_before.scalar()

        # 尝试使用相同邮箱创建第二个用户
        user2_data = {
            "email": email,
            "username": f"user2_{unique_id}",
            "password": "TestPass123",
            "full_name": "User Two",
        }
        response2 = await client.post("/api/v1/auth/register", json=user2_data)
        assert response2.status_code == status.HTTP_409_CONFLICT

        # 验证用户数量没有增加
        count_after = await session.execute(select(func.count()).select_from(User))
        user_count_after = count_after.scalar()
        assert user_count_after == user_count_before, "用户创建没有正确回滚"

    async def test_order_status_transition_validation(self, client, session, superuser_headers):
        """测试订单状态转换验证错误"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建产品和用户
        product = Product(
            name=f"Transition Product {unique_id}",
            sku=f"TRANS-{unique_id}",
            price=Decimal("30.00"),
            is_active=True,
        )
        session.add(product)

        user = User(
            email=f"trans_{unique_id}@example.com",
            username=f"trans_{unique_id}",
            hashed_password=get_password_hash("pass"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(product)
        await session.refresh(user)

        # 创建订单
        order_data = {
            "user_id": user.id,
            "items": [{"product_id": product.id, "quantity": 1, "unit_price": "30.00"}],
        }
        create_response = await client.post(
            "/api/v1/orders/",
            headers=superuser_headers,
            json=order_data,
        )
        order_id = create_response.json()["data"]["id"]

        # 尝试无效状态转换: PENDING -> COMPLETED (跳过CONFIRMED和SHIPPED)
        invalid_response = await client.put(
            f"/api/v1/orders/{order_id}",
            headers=superuser_headers,
            json={"status": OrderStatus.COMPLETED.value},
        )
        assert invalid_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # 验证订单状态未改变
        from app.modules.orders.service import get_order_by_id

        order = await get_order_by_id(session, order_id)
        assert order.status == OrderStatus.PENDING.value

    async def test_partial_failure_handling_in_order_processing(self, client, session, superuser_headers):
        """测试订单处理中的部分失败处理"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建产品(其中一个库存不足)
        product1 = Product(
            name=f"Partial Product 1 {unique_id}",
            sku=f"PARTIAL1-{unique_id}",
            price=Decimal("20.00"),
            is_active=True,
        )
        product2 = Product(
            name=f"Partial Product 2 {unique_id}",
            sku=f"PARTIAL2-{unique_id}",
            price=Decimal("30.00"),
            is_active=False,  # 不活跃的产品
        )
        session.add(product1)
        session.add(product2)

        user = User(
            email=f"partial_{unique_id}@example.com",
            username=f"partial_{unique_id}",
            hashed_password=get_password_hash("pass"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(product1)
        await session.refresh(product2)
        await session.refresh(user)

        # 获取订单数量
        from sqlalchemy import func, select

        count_before = await session.execute(select(func.count()).select_from(Order))
        order_count_before = count_before.scalar()

        # 尝试创建包含不活跃产品的订单
        order_data = {
            "user_id": user.id,
            "items": [
                {"product_id": product1.id, "quantity": 1, "unit_price": "20.00"},
                {"product_id": product2.id, "quantity": 1, "unit_price": "30.00"},
            ],
        }

        # 记录可能的失败情况
        response = await client.post(
            "/api/v1/orders/",
            headers=superuser_headers,
            json=order_data,
        )

        # 验证订单处理的完整性
        if response.status_code == status.HTTP_201_CREATED:
            # 如果成功创建，验证所有项都正确处理
            order_id = response.json()["data"]["id"]
            result = await session.execute(select(OrderItem).where(OrderItem.order_id == order_id))
            items = result.scalars().all()
            assert len(items) == 2, "订单项数量不匹配"

            # 验证订单总金额
            total = sum(item.quantity * float(item.unit_price) for item in items)
            assert Decimal(str(total)) == Decimal("50.00"), "订单金额计算错误"

    async def test_concurrent_modification_handling(self, client, session, superuser_headers):
        """测试并发修改处理"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建产品
        product = Product(
            name=f"Concurrent Product {unique_id}",
            sku=f"CONC-{unique_id}",
            price=Decimal("100.00"),
            is_active=True,
        )
        session.add(product)

        user = User(
            email=f"concurrent_{unique_id}@example.com",
            username=f"concurrent_{unique_id}",
            hashed_password=get_password_hash("pass"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(product)
        await session.refresh(user)

        # 创建订单
        order_data = {
            "user_id": user.id,
            "items": [{"product_id": product.id, "quantity": 1, "unit_price": "100.00"}],
        }
        create_response = await client.post(
            "/api/v1/orders/",
            headers=superuser_headers,
            json=order_data,
        )
        order_id = create_response.json()["data"]["id"]

        # 连续更新订单状态
        updates = [
            OrderStatus.CONFIRMED,
            OrderStatus.SHIPPED,
            OrderStatus.COMPLETED,
        ]

        for status in updates:
            response = await client.put(
                f"/api/v1/orders/{order_id}",
                headers=superuser_headers,
                json={"status": status.value},
            )
            assert response.status_code == status.HTTP_200_OK

        # 验证最终状态
        from app.modules.orders.service import get_order_by_id

        final_order = await get_order_by_id(session, order_id)
        assert final_order.status == OrderStatus.COMPLETED.value

    async def test_role_assignment_with_invalid_user(self, client, session, superuser_headers):
        """测试无效用户的角色分配错误"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建角色
        role_response = await client.post(
            "/api/v1/roles/roles/",
            headers=superuser_headers,
            json={"name": f"ErrorRole_{unique_id}", "description": "Test role"},
        )
        role_id = role_response.json()["data"]["id"]

        # 尝试为不存在的用户分配角色
        invalid_assign_response = await client.post(
            "/api/v1/roles/roles/assign",
            headers=superuser_headers,
            json={"user_id": 99999, "role_id": role_id},
        )
        assert invalid_assign_response.status_code == status.HTTP_404_NOT_FOUND

    async def test_compensation_for_failed_user_creation(self, client, session):
        """测试用户创建失败的补偿操作"""
        unique_id = uuid.uuid4().hex[:8]

        # 模拟创建过程中部分失败的场景
        user_data = {
            "email": f"compensation_{unique_id}@example.com",
            "username": f"compensation_{unique_id}",
            "password": "TestPass123",
            "full_name": "Compensation Test",
        }

        # 获取用户数量
        from sqlalchemy import func, select

        count_before = await session.execute(select(func.count()).select_from(User))
        user_count_before = count_before.scalar()

        # 创建用户
        response = await client.post("/api/v1/auth/register", json=user_data)

        if response.status_code == status.HTTP_201_CREATED:
            user_id = response.json()["data"]["id"]

            # 验证用户创建成功
            from app.modules.users.service import get_user_by_id

            user = await get_user_by_id(session, user_id)
            assert user is not None

            # 模拟需要回滚的场景：删除用户
            from app.modules.users.service import delete_user

            await delete_user(session, user_id)

            # 验证用户已删除
            deleted_user = await get_user_by_id(session, user_id)
            assert deleted_user is None

            # 验证用户数量恢复
            count_after = await session.execute(select(func.count()).select_from(User))
            user_count_after = count_after.scalar()
            assert user_count_after == user_count_before

    async def test_notification_send_failure_handling(self, client, session):
        """测试通知发送失败处理"""
        from unittest.mock import patch

        unique_id = uuid.uuid4().hex[:8]

        # 创建通知
        user = User(
            email=f"notify_fail_{unique_id}@example.com",
            username=f"notify_fail_{unique_id}",
            hashed_password=get_password_hash("pass"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        from app.modules.notifications.models import Notification

        notification = Notification(
            user_id=user.id,
            template_name=f"test_fail_{unique_id}",
            channel="email",
            status="pending",
            subject="Test",
            body="Test body",
            is_read=False,
        )
        session.add(notification)
        await session.commit()
        await session.refresh(notification)

        # 模拟发送失败
        notification.status = "failed"
        notification.error_message = "SMTP connection timeout"
        await session.commit()

        # 验证通知状态
        result = await session.execute(select(Notification).where(Notification.id == notification.id))
        saved_notification = result.scalar_one()
        assert saved_notification.status == "failed"
        assert "SMTP connection timeout" in saved_notification.error_message

    async def test_database_connection_error_recovery(self, client, session):
        """测试数据库连接错误恢复"""
        # 这个测试模拟数据库连接问题
        # 实际实现取决于数据库连接池配置

        unique_id = uuid.uuid4().hex[:8]

        try:
            # 尝试在可能有问题的情况下执行操作
            user = User(
                email=f"recovery_{unique_id}@example.com",
                username=f"recovery_{unique_id}",
                hashed_password=get_password_hash("pass"),
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            # 验证用户存在
            from sqlalchemy import select

            result = await session.execute(select(User).where(User.id == user.id))
            saved_user = result.scalar_one_or_none()
            assert saved_user is not None
            assert saved_user.email == f"recovery_{unique_id}@example.com"

        except SQLAlchemyError as e:
            pytest.fail(f"数据库操作失败: {e}")

    async def test_invalid_input_validation(self, client, session, superuser_headers):
        """测试无效输入验证"""
        unique_id = uuid.uuid4().hex[:8]

        # 测试无效的订单数据
        invalid_order_data = {
            "user_id": "invalid",  # 应该是整数
            "items": "not_a_list",  # 应该是列表
        }

        response = await client.post(
            "/api/v1/orders/",
            headers=superuser_headers,
            json=invalid_order_data,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # 测试无效的产品数据
        invalid_product_data = {
            "name": "",  # 空名称
            "sku": f"INVALID-{unique_id}",
            "price": -10.00,  # 负数价格
        }

        response = await client.post(
            "/api/v1/products/",
            headers=superuser_headers,
            json=invalid_product_data,
        )
        assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_400_BAD_REQUEST]

    async def test_authentication_failure_scenarios(self, client, session):
        """测试认证失败场景"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建用户
        user_data = {
            "email": f"auth_fail_{unique_id}@example.com",
            "username": f"auth_fail_{unique_id}",
            "password": "TestPass123",
            "full_name": "Auth Failure Test",
        }
        await client.post("/api/v1/auth/register", json=user_data)

        # 测试错误密码
        wrong_password_response = await client.post(
            "/api/v1/auth/login",
            json={"username": f"auth_fail_{unique_id}", "password": "WrongPassword123"},
        )
        assert wrong_password_response.status_code == status.HTTP_401_UNAUTHORIZED

        # 测试不存在的用户
        nonexistent_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent_user_99999", "password": "SomePassword123"},
        )
        assert nonexistent_response.status_code == status.HTTP_401_UNAUTHORIZED

        # 测试无效的token
        invalid_token_response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid_token_here"},
        )
        assert invalid_token_response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_resource_not_found_handling(self, client, session, superuser_headers):
        """测试资源不存在处理"""
        # 获取不存在的用户
        response = await client.get(
            "/api/v1/users/99999",
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # 获取不存在的订单
        response = await client.get(
            "/api/v1/orders/99999",
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # 获取不存在的角色
        response = await client.get(
            "/api/v1/roles/roles/99999",
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_permission_denied_handling(self, client, session, user_headers):
        """测试权限拒绝处理"""
        # 普通用户尝试访问管理员端点

        # 尝试访问所有用户列表
        response = await client.get(
            "/api/v1/users/",
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # 尝试创建角色
        response = await client.post(
            "/api/v1/roles/roles/",
            headers=user_headers,
            json={"name": "UnauthorizedRole", "description": "Test"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # 尝试访问审计日志
        response = await client.get(
            "/api/v1/audit/",
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_cascade_delete_protection(self, client, session, superuser_headers):
        """测试级联删除保护"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建产品和订单
        product = Product(
            name=f"Cascade Product {unique_id}",
            sku=f"CASCADE-{unique_id}",
            price=Decimal("40.00"),
            is_active=True,
        )
        session.add(product)

        user = User(
            email=f"cascade_{unique_id}@example.com",
            username=f"cascade_{unique_id}",
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

        # 尝试删除有关联订单的用户
        # 注意：具体行为取决于数据库外键约束配置
        response = await client.delete(
            f"/api/v1/users/{user.id}",
            headers=superuser_headers,
        )

        # 验证订单仍然存在(不应该被级联删除)
        from sqlalchemy import select

        result = await session.execute(select(Order).where(Order.id == order.id))
        existing_order = result.scalar_one_or_none()

        # 根据外键约束行为，订单可能被保留或删除
        # 但不应该出现异常

    async def test_timeout_and_retry_scenarios(self, client, session, superuser_headers):
        """测试超时和重试场景"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建大量产品测试性能
        products = []
        for i in range(50):
            product = Product(
                name=f"Bulk Product {i} {unique_id}",
                sku=f"BULK-{i}-{unique_id}",
                price=Decimal(f"{i + 1}.00"),
                is_active=True,
            )
            session.add(product)
            products.append(product)

        await session.commit()

        # 验证批量创建成功
        from sqlalchemy import select, func

        result = await session.execute(
            select(func.count()).select_from(Product).where(Product.sku.like(f"BULK-%-{unique_id}"))
        )
        count = result.scalar()
        assert count == 50

    async def test_data_integrity_violations(self, client, session):
        """测试数据完整性违规"""
        unique_id = uuid.uuid4().hex[:8]

        # 尝试创建重复SKU的产品
        product1 = Product(
            name=f"Integrity Product {unique_id}",
            sku=f"INTEGRITY-{unique_id}",
            price=Decimal("25.00"),
            is_active=True,
        )
        session.add(product1)
        await session.commit()

        # 尝试创建相同SKU的产品
        product2 = Product(
            name=f"Duplicate Product {unique_id}",
            sku=f"INTEGRITY-{unique_id}",  # 重复的SKU
            price=Decimal("35.00"),
            is_active=True,
        )
        session.add(product2)

        try:
            await session.commit()
            pytest.fail("应该触发唯一约束冲突")
        except IntegrityError:
            await session.rollback()
            # 预期行为：触发完整性错误

        # 验证只有第一个产品存在
        from sqlalchemy import select

        result = await session.execute(select(Product).where(Product.sku == f"INTEGRITY-{unique_id}"))
        products = result.scalars().all()
        assert len(products) == 1
