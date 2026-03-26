import uuid

import pytest

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.roles import service as permission_service
from app.modules.roles.schemas import PermissionCreate, PermissionUpdate


@pytest.mark.asyncio
class TestPermissionService:
    async def test_create_permission_success(self, session):
        unique_id = str(uuid.uuid4())[:8]
        perm_in = PermissionCreate(
            name=f"Test Permission {unique_id}", code=f"test:permission_{unique_id}", description="Test description"
        )
        permission = await permission_service.create_permission(session, perm_in)
        assert permission.name == f"Test Permission {unique_id}"
        assert permission.code == f"test:permission_{unique_id}"
        assert permission.description == "Test description"

    async def test_create_permission_duplicate_code(self, session):
        unique_id = str(uuid.uuid4())[:8]
        perm_in = PermissionCreate(name=f"First Permission {unique_id}", code=f"duplicate:code_{unique_id}")
        await permission_service.create_permission(session, perm_in)
        with pytest.raises(ConflictException) as exc_info:
            await permission_service.create_permission(session, perm_in)
        assert "already exists" in str(exc_info.value)

    async def test_update_permission_success(self, session):
        unique_id = str(uuid.uuid4())[:8]
        perm_in = PermissionCreate(
            name=f"Update Permission {unique_id}", code=f"update:permission_{unique_id}", description="Original"
        )
        permission = await permission_service.create_permission(session, perm_in)
        update_in = PermissionUpdate(description="Updated description")
        updated_perm = await permission_service.update_permission(session, permission.id, update_in)
        assert updated_perm.description == "Updated description"

    async def test_update_permission_not_found(self, session):
        update_in = PermissionUpdate(description="Updated description")
        with pytest.raises(NotFoundException) as exc_info:
            await permission_service.update_permission(session, 99999, update_in)
        assert "not found" in str(exc_info.value)

    async def test_delete_permission_success(self, session):
        unique_id = str(uuid.uuid4())[:8]
        perm_in = PermissionCreate(name=f"Delete Permission {unique_id}", code=f"delete:permission_{unique_id}")
        permission = await permission_service.create_permission(session, perm_in)
        deleted_perm = await permission_service.delete_permission(session, permission.id)
        assert deleted_perm.id == permission.id

    async def test_delete_permission_not_found(self, session):
        with pytest.raises(NotFoundException) as exc_info:
            await permission_service.delete_permission(session, 99999)
        assert "not found" in str(exc_info.value)

    async def test_get_permission_by_id(self, session):
        unique_id = str(uuid.uuid4())[:8]
        perm_in = PermissionCreate(name=f"Get Permission {unique_id}", code=f"get:permission_{unique_id}")
        created_perm = await permission_service.create_permission(session, perm_in)
        permission = await permission_service.get_permission_by_id(session, created_perm.id)
        assert permission is not None
        assert permission.name == f"Get Permission {unique_id}"

    async def test_get_permissions(self, session):
        unique_id = str(uuid.uuid4())[:8]
        perm_in = PermissionCreate(name=f"List Permission {unique_id}", code=f"list:permission_{unique_id}")
        await permission_service.create_permission(session, perm_in)
        permissions = await permission_service.get_permissions(session)
        assert len(permissions) > 0

    async def test_get_role_permissions(self, session):
        from app.modules.roles import service as role_service
        from app.modules.roles.schemas import RoleCreate

        unique_id = str(uuid.uuid4())[:8]
        perm_in = PermissionCreate(name=f"Role Permission {unique_id}", code=f"role:permission_{unique_id}")
        await permission_service.create_permission(session, perm_in)
        role_in = RoleCreate(name=f"permission_role_{unique_id}", description="Role with permission")
        role = await role_service.create_role(session, role_in)
        permissions = await permission_service.get_role_permissions(session, role.id)
        assert isinstance(permissions, list)
