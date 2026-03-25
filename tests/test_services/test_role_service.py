import pytest

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.roles import service as role_service
from app.modules.roles.schemas import RoleCreate, RoleUpdate


@pytest.mark.asyncio
class TestRoleService:
    async def test_create_role_success(self, session):
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        role_in = RoleCreate(name=f"test_role_{unique_id}", description="Test role")
        role = await role_service.create_role(session, role_in)
        assert role.name == f"test_role_{unique_id}"
        assert role.description == "Test role"

    async def test_create_role_duplicate_name(self, session):
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        role_in = RoleCreate(name=f"duplicate_role_{unique_id}", description="First role")
        await role_service.create_role(session, role_in)
        with pytest.raises(ConflictException) as exc_info:
            await role_service.create_role(session, role_in)
        assert "already exists" in str(exc_info.value)

    async def test_update_role_success(self, session):
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        role_in = RoleCreate(name=f"update_role_{unique_id}", description="Original description")
        role = await role_service.create_role(session, role_in)
        update_in = RoleUpdate(description="Updated description")
        updated_role = await role_service.update_role(session, role.id, update_in)
        assert updated_role.description == "Updated description"

    async def test_update_role_not_found(self, session):
        update_in = RoleUpdate(description="Updated description")
        with pytest.raises(NotFoundException) as exc_info:
            await role_service.update_role(session, 99999, update_in)
        assert "not found" in str(exc_info.value)

    async def test_delete_role_success(self, session):
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        role_in = RoleCreate(name=f"delete_role_{unique_id}", description="Role to delete")
        role = await role_service.create_role(session, role_in)
        deleted_role = await role_service.delete_role(session, role.id)
        assert deleted_role.id == role.id

    async def test_delete_role_not_found(self, session):
        with pytest.raises(NotFoundException) as exc_info:
            await role_service.delete_role(session, 99999)
        assert "not found" in str(exc_info.value)

    async def test_get_role_by_id(self, session):
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        role_in = RoleCreate(name=f"get_role_{unique_id}", description="Get role")
        created_role = await role_service.create_role(session, role_in)
        role = await role_service.get_role_by_id(session, created_role.id)
        assert role is not None
        assert role.name == f"get_role_{unique_id}"

    async def test_get_roles(self, session):
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        role_in = RoleCreate(name=f"list_role_{unique_id}", description="List role")
        await role_service.create_role(session, role_in)
        roles = await role_service.get_roles(session)
        assert len(roles) > 0

    async def test_assign_role_to_user(self, session, test_user):
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        role_in = RoleCreate(name=f"assign_role_{unique_id}", description="Assign role")
        role = await role_service.create_role(session, role_in)
        await role_service.assign_role_to_user(session, test_user.id, role.id)
        roles = await role_service.get_user_roles(session, test_user.id)
        assert any(r.id == role.id for r in roles)

    async def test_remove_role_from_user(self, session, test_user):
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        role_in = RoleCreate(name=f"remove_role_{unique_id}", description="Remove role")
        role = await role_service.create_role(session, role_in)
        await role_service.assign_role_to_user(session, test_user.id, role.id)
        await role_service.remove_role_from_user(session, test_user.id, role.id)
        roles = await role_service.get_user_roles(session, test_user.id)
        assert not any(r.id == role.id for r in roles)

    async def test_get_user_roles(self, session, test_user):
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        role_in = RoleCreate(name=f"user_role_{unique_id}", description="User role")
        role = await role_service.create_role(session, role_in)
        await role_service.assign_role_to_user(session, test_user.id, role.id)
        roles = await role_service.get_user_roles(session, test_user.id)
        assert len(roles) > 0

    async def test_check_user_permission(self, session, test_user):
        import uuid

        from app.modules.roles import service as permission_service
        from app.modules.roles.schemas import PermissionCreate

        unique_id = str(uuid.uuid4())[:8]
        perm_in = PermissionCreate(name=f"Test Permission {unique_id}", code=f"test:permission_{unique_id}")
        permission = await permission_service.create_permission(session, perm_in)
        role_in = RoleCreate(name=f"permission_role_{unique_id}", description="Permission role")
        role = await role_service.create_role(session, role_in)
        from app.modules.roles.repository import role_repo

        await role_repo.add_permission(session, role.id, permission.id)
        await role_service.assign_role_to_user(session, test_user.id, role.id)
        has_permission = await role_service.check_user_permission(
            session, test_user.id, f"test:permission_{unique_id}"
        )
        assert has_permission is True
