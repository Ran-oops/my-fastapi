"""
用户生命周期集成测试

测试完整流程: 注册 → 登录 → 获取信息 → 更新 → 删除
验证数据一致性、Token生命周期
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from jose import jwt

from app.core.config import settings
from app.core.security import ALGORITHM, verify_token
from app.modules.users.models import User


@pytest.mark.asyncio
class TestUserLifecycle:
    """用户完整生命周期测试"""

    async def test_full_user_lifecycle(self, client, session):
        """测试用户完整生命周期: 注册 → 登录 → 获取信息 → 更新 → 删除"""
        unique_id = uuid.uuid4().hex[:8]
        email = f"lifecycle_{unique_id}@example.com"
        username = f"lifecycle_user_{unique_id}"
        password = "TestPass123"
        full_name = "Lifecycle Test User"

        # Step 1: 注册
        register_data = {
            "email": email,
            "username": username,
            "password": password,
            "full_name": full_name,
        }
        register_response = await client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code == status.HTTP_201_CREATED

        register_result = register_response.json()
        assert register_result["data"]["email"] == email
        assert register_result["data"]["username"] == username
        assert register_result["data"]["full_name"] == full_name
        assert register_result["data"]["is_active"] is True
        user_id = register_result["data"]["id"]

        # 验证数据库中用户存在
        from sqlalchemy import select

        result = await session.execute(select(User).where(User.id == user_id))
        db_user = result.scalar_one_or_none()
        assert db_user is not None
        assert db_user.email == email
        assert db_user.hashed_password is not None
        assert db_user.hashed_password != password  # 密码已加密

        # Step 2: 登录
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        assert login_response.status_code == status.HTTP_200_OK

        login_result = login_response.json()["data"]
        access_token = login_result["access_token"]
        refresh_token = login_result["refresh_token"]
        assert access_token is not None
        assert refresh_token is not None
        assert login_result["token_type"] == "bearer"

        # 验证Token有效性
        decoded = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["sub"] == str(user_id)
        assert decoded["type"] == "access"
        assert "exp" in decoded
        assert "iat" in decoded

        # Step 3: 获取用户信息
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = await client.get("/api/v1/users/me", headers=headers)
        assert me_response.status_code == status.HTTP_200_OK

        me_data = me_response.json()["data"]
        assert me_data["id"] == user_id
        assert me_data["email"] == email
        assert me_data["username"] == username
        assert me_data["full_name"] == full_name
        assert me_data["is_active"] is True
        assert me_data["is_superuser"] is False
        assert "created_at" in me_data
        assert "updated_at" in me_data

        # Step 4: 更新用户信息
        new_full_name = "Updated Lifecycle User"
        update_response = await client.put(
            f"/api/v1/users/{user_id}",
            headers=headers,
            json={"full_name": new_full_name},
        )
        assert update_response.status_code == status.HTTP_200_OK

        update_result = update_response.json()
        assert update_result["data"]["full_name"] == new_full_name
        assert update_result["data"]["email"] == email  # 未变更
        assert update_result["message"] == "User updated successfully"

        # 验证数据库已更新
        await session.refresh(db_user)
        assert db_user.full_name == new_full_name

        # 重新获取信息确认更新
        me_response2 = await client.get("/api/v1/users/me", headers=headers)
        assert me_response2.json()["data"]["full_name"] == new_full_name

        # Step 5: 删除用户 (需要superuser权限)
        # 先创建一个superuser来删除
        from app.core.security import get_password_hash

        admin_email = f"admin_delete_{unique_id}@example.com"
        admin_username = f"admin_delete_{unique_id}"
        admin_user = User(
            email=admin_email,
            username=admin_username,
            hashed_password=get_password_hash("AdminPass123"),
            full_name="Admin For Delete",
            is_active=True,
            is_superuser=True,
        )
        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)

        # 使用superuser删除用户
        admin_token = jwt.encode(
            {
                "sub": str(admin_user.id),
                "type": "access",
                "iat": datetime.now(UTC),
                "exp": datetime.now(UTC) + timedelta(minutes=30),
            },
            settings.SECRET_KEY,
            algorithm=ALGORITHM,
        )
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        delete_response = await client.delete(
            f"/api/v1/users/{user_id}",
            headers=admin_headers,
        )
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # 验证用户已删除
        result = await session.execute(select(User).where(User.id == user_id))
        deleted_user = result.scalar_one_or_none()
        assert deleted_user is None

        # 验证原token无法获取已删除用户的信息
        me_response_after_delete = await client.get("/api/v1/users/me", headers=headers)
        # 应该返回404因为用户不存在
        assert me_response_after_delete.status_code == status.HTTP_404_NOT_FOUND

    async def test_token_lifecycle(self, client, session):
        """测试Token完整生命周期"""
        unique_id = uuid.uuid4().hex[:8]
        username = f"token_test_{unique_id}"
        password = "TestPass123"

        # 创建用户
        register_data = {
            "email": f"token_{unique_id}@example.com",
            "username": username,
            "password": password,
            "full_name": "Token Test User",
        }
        await client.post("/api/v1/auth/register", json=register_data)

        # 初始登录
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        login_result = login_response.json()["data"]
        access_token = login_result["access_token"]
        refresh_token = login_result["refresh_token"]

        # 使用access token访问
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = await client.get("/api/v1/users/me", headers=headers)
        assert me_response.status_code == status.HTTP_200_OK

        # 验证token类型区分
        decoded_access = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        decoded_refresh = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded_access["type"] == "access"
        assert decoded_refresh["type"] == "refresh"

        # 验证token过期时间
        access_exp = datetime.fromtimestamp(decoded_access["exp"], tz=UTC)
        refresh_exp = datetime.fromtimestamp(decoded_refresh["exp"], tz=UTC)
        assert refresh_exp > access_exp  # refresh token应该比access token过期时间更长

        # 刷新token
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"access_token": access_token, "refresh_token": refresh_token},
        )
        assert refresh_response.status_code == status.HTTP_200_OK

        refresh_result = refresh_response.json()["data"]
        new_access_token = refresh_result["access_token"]
        new_refresh_token = refresh_result["refresh_token"]

        # 验证新token与原token不同
        assert new_access_token != access_token
        assert new_refresh_token != refresh_token

        # 验证新token有效
        new_headers = {"Authorization": f"Bearer {new_access_token}"}
        me_response2 = await client.get("/api/v1/users/me", headers=new_headers)
        assert me_response2.status_code == status.HTTP_200_OK

        # 验证新token的用户信息一致
        assert me_response2.json()["data"]["username"] == username

    async def test_user_data_consistency_throughout_lifecycle(self, client, session):
        """测试用户数据在生命周期中的一致性"""
        unique_id = uuid.uuid4().hex[:8]
        email = f"consistency_{unique_id}@example.com"
        username = f"consistency_user_{unique_id}"
        password = "TestPass123"

        # 注册
        register_data = {
            "email": email,
            "username": username,
            "password": password,
            "full_name": "Consistency Test",
        }
        register_response = await client.post("/api/v1/auth/register", json=register_data)
        user_id = register_response.json()["data"]["id"]

        # 登录
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        token = login_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 验证各端点数据一致性
        me_response = await client.get("/api/v1/users/me", headers=headers)
        me_data = me_response.json()["data"]

        # 通过ID获取
        user_response = await client.get(f"/api/v1/users/{user_id}", headers=headers)
        user_data = user_response.json()["data"]

        # 数据应该一致
        assert me_data["id"] == user_data["id"]
        assert me_data["email"] == user_data["email"]
        assert me_data["username"] == user_data["username"]
        assert me_data["full_name"] == user_data["full_name"]
        assert me_data["is_active"] == user_data["is_active"]
        assert me_data["created_at"] == user_data["created_at"]

        # 更新后再次验证一致性
        await client.put(
            f"/api/v1/users/{user_id}",
            headers=headers,
            json={"full_name": "Updated Name"},
        )

        me_response2 = await client.get("/api/v1/users/me", headers=headers)
        user_response2 = await client.get(f"/api/v1/users/{user_id}", headers=headers)
        assert me_response2.json()["data"]["full_name"] == user_response2.json()["data"]["full_name"]

    async def test_user_cannot_delete_self(self, client, session, user_headers, test_user):
        """测试用户不能删除自己(需要superuser权限)"""
        delete_response = await client.delete(
            f"/api/v1/users/{test_user.id}",
            headers=user_headers,
        )
        # 应该返回403 Forbidden
        assert delete_response.status_code == status.HTTP_403_FORBIDDEN

    async def test_user_can_only_update_self(self, client, session, test_user, user_token):
        """测试普通用户只能更新自己"""
        # 创建另一个用户
        from app.core.security import get_password_hash

        other_user = User(
            email="other@test.com",
            username="otheruser",
            hashed_password=get_password_hash("pass123"),
            full_name="Other User",
            is_active=True,
        )
        session.add(other_user)
        await session.commit()

        headers = {"Authorization": f"Bearer {user_token}"}

        # 尝试更新其他用户
        update_response = await client.put(
            f"/api/v1/users/{other_user.id}",
            headers=headers,
            json={"full_name": "Hacked Name"},
        )
        assert update_response.status_code == status.HTTP_403_FORBIDDEN

        # 可以更新自己
        self_update = await client.put(
            f"/api/v1/users/{test_user.id}",
            headers=headers,
            json={"full_name": "My New Name"},
        )
        assert self_update.status_code == status.HTTP_200_OK
