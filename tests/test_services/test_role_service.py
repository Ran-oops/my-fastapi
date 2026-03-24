import pytest

from app.core.exceptions import ConflictException, NotFoundException
from app.schemas.role import RoleCreate, RoleUpdate
from app.services.role import role_service


@pytest.mark.asyncio
class TestRoleService:
    async def test_create_role_success(self, db_session):
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        role_in = RoleCreate(name=f"test_role_{unique_id}", description="Test role")
        role = await role_service.create_role(db_session, role_in)
        assert role.name == f"test_role_{unique_id}"
        assert role.description == "Test role"

    async def test_create_role_duplicate_name(self, db_session):
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        role_in = RoleCreate(name=f"duplicate_role_{unique_id}", description="First role")
        await role_service.create_role(db_session, role_in)
        with pytest.raises(ConflictException) as exc_info:
            await role_service.create_role(db_session, role_in)
        assert "already exists" in str(exc_info.value)

    async def test_update_role_success(self, db_session):
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        role_in = RoleCreate(name=f"update_role_{unique_id}", description="Original description")
        role = await role_service.create_role(db_session, role_in)
        update_in = RoleUpdate(description="Updated description")
        updated_role = await role_service.update_role(db_session, role.id, update_in)
        assert updated_role.description == "Updated description"

    async def test_update_role_not_found(self, db_session):
        update_in = RoleUpdate(description="Updated description")
        with pytest.raises(NotFoundException) as exc_info:
            await role_service.update_role(db_session, 99999, update_in)
        assert "not found" in str(exc_info.value)

    async def test_delete_role_success(self, db_session):
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        role_in = RoleCreate(name=f"delete_role_{unique_id}", description="Role to delete")
        role = await role_service.create_role(db_session, role_in)
        deleted_role = await role_service.delete_role(db_session, role.id)
        assert deleted_role.id == role.id

    async def test_delete_role_not_found(self, db_session):
        with pytest.raises(NotFoundException) as exc_info:
            await role_service.delete_role(db_session, 99999)
        assert "not found" in str(exc_info.value)

    async def test_get_role_by_id(self, db_session):
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        role_in = RoleCreate(name=f"get_role_{unique_id}", description="Get role")
        created_role = await role_service.create_role(db_session, role_in)
        role = await role_service.get_role_by_id(db_session, created_role.id)
        assert role is not None
        assert role.name == f"get_role_{unique_id}"

    async def test_get_roles(self, db_session):
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        role_in = RoleCreate(name=f"list_role_{unique_id}", description="List role")
        await role_service.create_role(db_session, role_in)
        roles = await role_service.get_roles(db_session)
        assert len(roles) > 0

    async def test_assign_role_to_user(self, db_session, test_user):
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        role_in = RoleCreate(name=f"assign_role_{unique_id}", description="Assign role")
        role = await role_service.create_role(db_session, role_in)
        await role_service.assign_role_to_user(db_session, test_user.id, role.id)
        roles = await role_service.get_user_roles(db_session, test_user.id)
        assert any(r.id == role.id for r in roles)

    async def test_remove_role_from_user(self, db_session, test_user):
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        role_in = RoleCreate(name=f"remove_role_{unique_id}", description="Remove role")
        role = await role_service.create_role(db_session, role_in)
        await role_service.assign_role_to_user(db_session, test_user.id, role.id)
        await role_service.remove_role_from_user(db_session, test_user.id, role.id)
        roles = await role_service.get_user_roles(db_session, test_user.id)
        assert not any(r.id == role.id for r in roles)

    async def test_get_user_roles(self, db_session, test_user):
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        role_in = RoleCreate(name=f"user_role_{unique_id}", description="User role")
        role = await role_service.create_role(db_session, role_in)
        await role_service.assign_role_to_user(db_session, test_user.id, role.id)
        roles = await role_service.get_user_roles(db_session, test_user.id)
        assert len(roles) > 0

    async def test_check_user_permission(self, db_session, test_user):
        import uuid

        from app.schemas.permission import PermissionCreate
        from app.services.permission import permission_service

        unique_id = str(uuid.uuid4())[:8]
        perm_in = PermissionCreate(name=f"Test Permission {unique_id}", code=f"test:permission_{unique_id}")
        permission = await permission_service.create_permission(db_session, perm_in)
        role_in = RoleCreate(name=f"permission_role_{unique_id}", description="Permission role")
        role = await role_service.create_role(db_session, role_in)
        # Add permission to role
        from app.crud.role import role as role_crud

        await role_crud.add_permission(db_session, role.id, permission.id)
        await role_service.assign_role_to_user(db_session, test_user.id, role.id)
        has_permission = await role_service.check_user_permission(
            db_session, test_user.id, f"test:permission_{unique_id}"
        )
        assert has_permission is True
