"""
角色权限流程集成测试

测试完整流程: 创建角色 → 分配权限 → 分配给用户 → 验证权限
测试权限继承、权限撤销
"""

import uuid

import pytest
from fastapi import status
from sqlalchemy import select

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.roles.models import Permission, Role
from app.modules.roles import service as role_service
from app.modules.roles.schemas import (
    PermissionCreate,
    RoleCreate,
    RoleUpdate,
    UserRoleAssign,
)
from app.modules.users.models import User
from app.core.security import get_password_hash


@pytest.mark.asyncio
class TestRolePermissionFlow:
    """角色权限完整流程测试"""

    async def test_full_role_permission_flow(self, client, session, superuser_headers):
        """测试完整角色权限流程: 创建角色 → 分配权限 → 分配给用户 → 验证权限"""
        unique_id = uuid.uuid4().hex[:8]

        # Step 1: 创建权限
        permissions = []
        perm_codes = ["users:read", "users:write", "orders:read", "orders:admin"]
        for i, code in enumerate(perm_codes):
            perm_data = PermissionCreate(
                name=f"Permission {code} {unique_id}",
                code=f"{code}_{unique_id}",
                description=f"Test permission for {code}",
            )
            perm = await role_service.create_permission(session, perm_data)
            permissions.append(perm)
            assert perm.id is not None
            assert perm.code == f"{code}_{unique_id}"

        # Step 2: 创建角色
        role_data = RoleCreate(
            name=f"TestRole_{unique_id}",
            description=f"Test role for integration {unique_id}",
        )
        role = await role_service.create_role(session, role_data)
        assert role.id is not None
        assert role.name == f"TestRole_{unique_id}"

        # 通过API创建角色
        role_response = await client.post(
            "/api/v1/roles/roles/",
            headers=superuser_headers,
            json={"name": f"APIRole_{unique_id}", "description": "API created role"},
        )
        assert role_response.status_code == status.HTTP_201_CREATED
        api_role_id = role_response.json()["data"]["id"]

        # Step 3: 分配权限给角色 (通过数据库关联)
        # 获取角色和权限的完整对象
        result = await session.execute(select(Role).where(Role.id == role.id))
        db_role = result.scalar_one()

        result = await session.execute(select(Permission).where(Permission.id.in_([p.id for p in permissions[:2]])))
        db_permissions = result.scalars().all()

        # 关联权限
        for perm in db_permissions:
            if perm not in db_role.permissions:
                db_role.permissions.append(perm)

        await session.commit()
        await session.refresh(db_role)

        # 验证权限已分配
        assert len(db_role.permissions) == 2
        perm_codes = [p.code for p in db_role.permissions]
        assert f"users:read_{unique_id}" in perm_codes
        assert f"users:write_{unique_id}" in perm_codes

        # Step 4: 创建用户
        user = User(
            email=f"role_test_{unique_id}@example.com",
            username=f"role_test_{unique_id}",
            hashed_password=get_password_hash("TestPass123"),
            full_name="Role Test User",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Step 5: 分配角色给用户
        assign_response = await client.post(
            "/api/v1/roles/roles/assign",
            headers=superuser_headers,
            json={"user_id": user.id, "role_id": role.id},
        )
        assert assign_response.status_code == status.HTTP_200_OK
        assert assign_response.json()["data"]["user_id"] == user.id
        assert assign_response.json()["data"]["role_id"] == role.id

        # 验证数据库关联
        result = await session.execute(select(User).where(User.id == user.id))
        db_user = result.scalar_one()
        await session.refresh(db_user, ["roles"])

        user_role_ids = [r.id for r in db_user.roles]
        assert role.id in user_role_ids

        # Step 6: 验证用户权限
        user_roles_response = await client.get(
            f"/api/v1/roles/roles/users/{user.id}",
            headers=superuser_headers,
        )
        assert user_roles_response.status_code == status.HTTP_200_OK
        roles_data = user_roles_response.json()["data"]
        role_names = [r["name"] for r in roles_data]
        assert f"TestRole_{unique_id}" in role_names

        # 验证角色权限
        role_perms_response = await client.get(
            f"/api/v1/roles/permissions/roles/{role.id}",
            headers=superuser_headers,
        )
        assert role_perms_response.status_code == status.HTTP_200_OK
        perms_data = role_perms_response.json()["data"]
        assert len(perms_data) == 2

        # Step 7: 验证权限检查
        has_perm = await role_service.check_user_permission(session, user.id, f"users:read_{unique_id}")
        assert has_perm is True

        has_no_perm = await role_service.check_user_permission(session, user.id, f"orders:admin_{unique_id}")
        assert has_no_perm is False

    async def test_permission_inheritance(self, client, session, superuser_headers):
        """测试权限继承: 多个角色的权限合并"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建权限
        perm1 = await role_service.create_permission(
            session, PermissionCreate(name=f"Perm1_{unique_id}", code=f"perm1_{unique_id}")
        )
        perm2 = await role_service.create_permission(
            session, PermissionCreate(name=f"Perm2_{unique_id}", code=f"perm2_{unique_id}")
        )
        perm3 = await role_service.create_permission(
            session, PermissionCreate(name=f"Perm3_{unique_id}", code=f"perm3_{unique_id}")
        )

        # 创建两个角色
        role1 = await role_service.create_role(session, RoleCreate(name=f"Role1_{unique_id}", description="First role"))
        role2 = await role_service.create_role(
            session, RoleCreate(name=f"Role2_{unique_id}", description="Second role")
        )

        # 为角色1分配权限1
        db_role1 = await session.get(Role, role1.id)
        db_perm1 = await session.get(Permission, perm1.id)
        db_role1.permissions.append(db_perm1)

        # 为角色2分配权限2和权限3
        db_role2 = await session.get(Role, role2.id)
        db_perm2 = await session.get(Permission, perm2.id)
        db_perm3 = await session.get(Permission, perm3.id)
        db_role2.permissions.append(db_perm2)
        db_role2.permissions.append(db_perm3)

        await session.commit()

        # 创建用户并分配两个角色
        user = User(
            email=f"inherit_{unique_id}@example.com",
            username=f"inherit_{unique_id}",
            hashed_password=get_password_hash("pass"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # 通过API分配角色
        await client.post(
            "/api/v1/roles/roles/assign",
            headers=superuser_headers,
            json={"user_id": user.id, "role_id": role1.id},
        )
        await client.post(
            "/api/v1/roles/roles/assign",
            headers=superuser_headers,
            json={"user_id": user.id, "role_id": role2.id},
        )

        # 验证用户继承所有权限
        assert await role_service.check_user_permission(session, user.id, f"perm1_{unique_id}") is True
        assert await role_service.check_user_permission(session, user.id, f"perm2_{unique_id}") is True
        assert await role_service.check_user_permission(session, user.id, f"perm3_{unique_id}") is True

        # 获取用户所有角色
        user_roles = await role_service.get_user_roles(session, user.id)
        assert len(user_roles) == 2
        role_names = [r.name for r in user_roles]
        assert f"Role1_{unique_id}" in role_names
        assert f"Role2_{unique_id}" in role_names

    async def test_permission_revoke(self, client, session, superuser_headers):
        """测试权限撤销: 移除角色、移除权限"""
        unique_id = uuid.uuid4().hex[:8]

        # 创建权限和角色
        perm = await role_service.create_permission(
            session, PermissionCreate(name=f"RevokePerm_{unique_id}", code=f"revoke_{unique_id}")
        )
        role = await role_service.create_role(
            session, RoleCreate(name=f"RevokeRole_{unique_id}", description="Role to revoke")
        )

        # 关联权限
        db_role = await session.get(Role, role.id)
        db_perm = await session.get(Permission, perm.id)
        db_role.permissions.append(db_perm)
        await session.commit()

        # 创建用户并分配角色
        user = User(
            email=f"revoke_{unique_id}@example.com",
            username=f"revoke_{unique_id}",
            hashed_password=get_password_hash("pass"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        await client.post(
            "/api/v1/roles/roles/assign",
            headers=superuser_headers,
            json={"user_id": user.id, "role_id": role.id},
        )

        # 验证用户有权限
        assert await role_service.check_user_permission(session, user.id, f"revoke_{unique_id}") is True

        # 撤销角色分配
        revoke_response = await client.delete(
            f"/api/v1/roles/roles/assign/{user.id}/{role.id}",
            headers=superuser_headers,
        )
        assert revoke_response.status_code == status.HTTP_204_NO_CONTENT

        # 验证用户失去权限
        assert await role_service.check_user_permission(session, user.id, f"revoke_{unique_id}") is False

        # 重新分配角色以测试权限撤销
        await client.post(
            "/api/v1/roles/roles/assign",
            headers=superuser_headers,
            json={"user_id": user.id, "role_id": role.id},
        )
        assert await role_service.check_user_permission(session, user.id, f"revoke_{unique_id}") is True

        # 从角色移除权限
        db_role = await session.get(Role, role.id)
        db_perm = await session.get(Permission, perm.id)
        db_role.permissions.remove(db_perm)
        await session.commit()

        # 验证用户失去权限(通过权限移除)
        assert await role_service.check_user_permission(session, user.id, f"revoke_{unique_id}") is False

    async def test_role_cannot_be_deleted_with_users(self, client, session, superuser_headers):
        """测试有用户的角色不能被删除"""
        unique_id = uuid.uuid4().hex[:8]

        role = await role_service.create_role(
            session, RoleCreate(name=f"ProtectedRole_{unique_id}", description="Cannot delete")
        )

        user = User(
            email=f"protected_{unique_id}@example.com",
            username=f"protected_{unique_id}",
            hashed_password=get_password_hash("pass"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # 分配角色
        await client.post(
            "/api/v1/roles/roles/assign",
            headers=superuser_headers,
            json={"user_id": user.id, "role_id": role.id},
        )

        # 尝试删除角色
        delete_response = await client.delete(
            f"/api/v1/roles/roles/{role.id}",
            headers=superuser_headers,
        )
        assert delete_response.status_code == status.HTTP_409_CONFLICT

    async def test_permission_cannot_be_deleted_with_roles(self, client, session, superuser_headers):
        """测试有关联角色的权限不能被删除"""
        unique_id = uuid.uuid4().hex[:8]

        perm = await role_service.create_permission(
            session, PermissionCreate(name=f"ProtectedPerm_{unique_id}", code=f"protected_{unique_id}")
        )

        role = await role_service.create_role(
            session, RoleCreate(name=f"RoleWithPerm_{unique_id}", description="Has permission")
        )

        # 关联权限和角色
        db_role = await session.get(Role, role.id)
        db_perm = await session.get(Permission, perm.id)
        db_role.permissions.append(db_perm)
        await session.commit()

        # 尝试删除权限
        delete_response = await client.delete(
            f"/api/v1/roles/permissions/{perm.id}",
            headers=superuser_headers,
        )
        assert delete_response.status_code == status.HTTP_409_CONFLICT

    async def test_role_update_propagation(self, client, session, superuser_headers):
        """测试角色更新传播到用户"""
        unique_id = uuid.uuid4().hex[:8]

        role = await role_service.create_role(
            session, RoleCreate(name=f"UpdateRole_{unique_id}", description="Original description")
        )

        # 通过API更新角色
        update_response = await client.put(
            f"/api/v1/roles/roles/{role.id}",
            headers=superuser_headers,
            json={"name": f"UpdatedRole_{unique_id}", "description": "Updated description"},
        )
        assert update_response.status_code == status.HTTP_200_OK

        updated = update_response.json()["data"]
        assert updated["name"] == f"UpdatedRole_{unique_id}"
        assert updated["description"] == "Updated description"

        # 创建用户并分配更新后的角色
        user = User(
            email=f"update_test_{unique_id}@example.com",
            username=f"update_test_{unique_id}",
            hashed_password=get_password_hash("pass"),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        await client.post(
            "/api/v1/roles/roles/assign",
            headers=superuser_headers,
            json={"user_id": user.id, "role_id": role.id},
        )

        # 验证用户获取到的是更新后的角色信息
        user_roles = await client.get(
            f"/api/v1/roles/roles/users/{user.id}",
            headers=superuser_headers,
        )
        roles = user_roles.json()["data"]
        role_names = [r["name"] for r in roles]
        assert f"UpdatedRole_{unique_id}" in role_names
