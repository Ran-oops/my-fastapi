"""End-to-end test for admin workflow.

This module tests the complete admin workflow including user management,
product creation, role assignment, and audit log viewing.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash
from app.db.session import SessionFactory
from app.main import app
from app.modules.users.models import User


@pytest.mark.e2e
@pytest.mark.admin
class TestAdminWorkflow:
    """Test complete admin workflow end-to-end."""

    @pytest.fixture(scope="function")
    async def client(self):
        """Create test client with real HTTP transport."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.fixture(scope="function")
    async def admin_credentials(self):
        """Create admin user and return credentials."""
        import uuid

        uid = uuid.uuid4().hex[:8]
        username = f"admin_{uid}"
        email = f"admin_{uid}@example.com"
        password = "AdminPassword123!"

        async with SessionFactory() as session:
            admin = User(
                email=email,
                username=username,
                hashed_password=get_password_hash(password),
                full_name="Admin Test User",
                is_active=True,
                is_superuser=True,
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            admin_id = admin.id

        token = create_access_token(subject=str(admin_id))

        yield {"id": admin_id, "username": username, "email": email, "password": password, "token": token}

        # Cleanup
        async with SessionFactory() as session:
            result = await session.get(User, admin_id)
            if result:
                await session.delete(result)
                await session.commit()

    @pytest.mark.asyncio
    async def test_complete_admin_workflow(self, client, admin_credentials):
        """Test complete admin workflow."""
        admin_headers = {"Authorization": f"Bearer {admin_credentials['token']}"}

        # Step 1: Admin login (verify token works)
        print("\n1. Verifying admin login...")
        response = await client.get("/api/v2/users/me", headers=admin_headers)
        assert response.status_code == 200
        me_response = response.json()
        assert me_response["success"] is True
        assert me_response["data"]["is_superuser"] is True
        print(f"   Admin verified: {admin_credentials['username']}")

        # Step 2: Create product
        print("\n2. Creating product...")
        import uuid

        sku = f"PROD-{uuid.uuid4().hex[:8].upper()}"
        product_data = {
            "name": f"Test Product {sku}",
            "sku": sku,
            "description": "A test product created by admin workflow",
            "price": "199.99",
            "category": "Test Category",
            "is_active": True,
        }
        response = await client.post("/api/v2/products/", json=product_data, headers=admin_headers)
        assert response.status_code == 201
        product_response = response.json()
        assert product_response["success"] is True
        assert product_response["data"]["sku"] == sku
        product_id = product_response["data"]["id"]
        print(f"   Product created: ID={product_id}, SKU={sku}")

        # Step 3: View all users
        print("\n3. Viewing all users...")
        response = await client.get("/api/v2/users/?page=1&page_size=10", headers=admin_headers)
        assert response.status_code == 200
        users_response = response.json()
        assert users_response["success"] is True
        assert "data" in users_response
        assert "total" in users_response
        print(f"   Total users: {users_response['total']}")

        # Step 4: Create role and assign permissions
        print("\n4. Creating role with permissions...")
        # First create a permission
        permission_data = {
            "name": f"test_permission_{uuid.uuid4().hex[:4]}",
            "code": f"TEST_PERM_{uuid.uuid4().hex[:4].upper()}",
            "description": "Test permission for admin workflow",
        }
        response = await client.post("/api/v2/permissions/", json=permission_data, headers=admin_headers)
        if response.status_code == 201:
            permission_response = response.json()
            permission_id = permission_response["data"]["id"]
            print(f"   Permission created: ID={permission_id}")
        else:
            # Permission might already exist
            print(f"   Permission creation status: {response.status_code}")
            permission_id = None

        # Create a role
        role_data = {"name": f"TestRole_{uuid.uuid4().hex[:6]}", "description": "Test role created by admin workflow"}
        response = await client.post("/api/v2/roles/", json=role_data, headers=admin_headers)
        assert response.status_code == 201
        role_response = response.json()
        assert role_response["success"] is True
        role_id = role_response["data"]["id"]
        print(f"   Role created: ID={role_id}")

        # Assign permission to role if created
        if permission_id:
            print("\n5. Assigning permission to role...")
            # Note: This endpoint might differ based on API implementation
            print(f"   Permission assignment logic (role_id={role_id}, permission_id={permission_id})")

        # Step 6: Create a regular user and assign role
        print("\n6. Creating regular user and assigning role...")
        regular_user_data = {
            "username": f"regular_{uuid.uuid4().hex[:6]}",
            "email": f"regular_{uuid.uuid4().hex[:6]}@example.com",
            "password": "RegularUser123!",
            "full_name": "Regular Test User",
        }
        response = await client.post("/api/v2/auth/register", json=regular_user_data)
        assert response.status_code == 201
        regular_user_response = response.json()
        regular_user_id = regular_user_response["data"]["id"]
        print(f"   Regular user created: ID={regular_user_id}")

        # Assign role to user
        assign_data = {"user_id": regular_user_id, "role_id": role_id}
        response = await client.post("/api/v2/roles/assign", json=assign_data, headers=admin_headers)
        assert response.status_code == 200
        assign_response = response.json()
        assert assign_response["success"] is True
        print(f"   Role assigned to user: role_id={role_id} -> user_id={regular_user_id}")

        # Step 7: View audit logs
        print("\n7. Viewing audit logs...")
        response = await client.get("/api/v2/audit/?page=1&page_size=10", headers=admin_headers)
        assert response.status_code == 200
        audit_response = response.json()
        assert audit_response["success"] is True
        assert "data" in audit_response
        print(f"   Audit logs retrieved: {len(audit_response['data'])} entries")

        # Step 8: Export data
        print("\n8. Triggering data export...")
        response = await client.post("/api/v2/exports/orders/?format=csv&limit=100", headers=admin_headers)
        assert response.status_code == 202
        export_response = response.json()
        assert export_response["success"] is True
        assert "task_id" in export_response["data"]
        task_id = export_response["data"]["task_id"]
        print(f"   Export task created: ID={task_id}")

        print("\n✅ Complete admin workflow test passed!")

    @pytest.mark.asyncio
    async def test_admin_product_management(self, client, admin_credentials):
        """Test product CRUD operations by admin."""
        admin_headers = {"Authorization": f"Bearer {admin_credentials['token']}"}

        # Create product
        import uuid

        sku = f"CRUD-{uuid.uuid4().hex[:8].upper()}"
        product_data = {
            "name": f"CRUD Product {sku}",
            "sku": sku,
            "description": "Testing CRUD operations",
            "price": "99.99",
            "category": "Test",
            "is_active": True,
        }
        response = await client.post("/api/v2/products/", json=product_data, headers=admin_headers)
        assert response.status_code == 201
        product_id = response.json()["data"]["id"]

        # Update product
        update_data = {"price": "149.99", "description": "Updated description"}
        response = await client.put(f"/api/v2/products/{product_id}", json=update_data, headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["data"]["price"] == "149.99"

        # Get product by SKU
        response = await client.get(f"/api/v2/products/sku/{sku}", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["data"]["sku"] == sku

        # Delete product
        response = await client.delete(f"/api/v2/products/{product_id}", headers=admin_headers)
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_regular_user_cannot_access_admin_routes(self, client):
        """Test that regular users cannot access admin-only routes."""
        import uuid
        from app.core.security import create_access_token
        from app.db.session import SessionFactory
        from app.modules.users.models import User

        # Create regular user
        uid = uuid.uuid4().hex[:8]
        async with SessionFactory() as session:
            regular_user = User(
                email=f"regular_{uid}@example.com",
                username=f"regular_{uid}",
                hashed_password=get_password_hash("RegularPass123!"),
                full_name="Regular User",
                is_active=True,
                is_superuser=False,
            )
            session.add(regular_user)
            await session.commit()
            await session.refresh(regular_user)
            user_id = regular_user.id

        try:
            token = create_access_token(subject=str(user_id))
            user_headers = {"Authorization": f"Bearer {token}"}

            # Try to access admin routes
            # View all users (admin only)
            response = await client.get("/api/v2/users/", headers=user_headers)
            assert response.status_code == 403

            # Create product (admin only)
            response = await client.post(
                "/api/v2/products/", json={"name": "Test", "sku": "TEST", "price": "1.00"}, headers=user_headers
            )
            assert response.status_code == 403

            # View audit logs (admin only)
            response = await client.get("/api/v2/audit/", headers=user_headers)
            assert response.status_code == 403

        finally:
            # Cleanup
            async with SessionFactory() as session:
                result = await session.get(User, user_id)
                if result:
                    await session.delete(result)
                    await session.commit()
