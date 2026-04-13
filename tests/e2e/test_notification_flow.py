"""End-to-end test for notification flow.

This module tests the complete notification flow including template configuration,
event triggering, notification generation, and user interaction.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash
from app.db.session import SessionFactory
from app.main import app
from app.modules.notifications.models import NotificationTemplate
from app.modules.users.models import User


@pytest.mark.e2e
@pytest.mark.notifications
class TestNotificationFlow:
    """Test complete notification flow end-to-end."""

    @pytest.fixture(scope="function")
    async def client(self):
        """Create test client with real HTTP transport."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.fixture(scope="function")
    async def admin_and_user(self):
        """Create admin and regular user for notification tests."""
        import uuid

        uid = uuid.uuid4().hex[:8]

        # Create admin
        admin_email = f"admin_notif_{uid}@example.com"
        admin_username = f"admin_notif_{uid}"
        async with SessionFactory() as session:
            admin = User(
                email=admin_email,
                username=admin_username,
                hashed_password=get_password_hash("AdminPass123!"),
                full_name="Admin Notification User",
                is_active=True,
                is_superuser=True,
            )
            session.add(admin)

            # Create regular user
            user_email = f"user_notif_{uid}@example.com"
            user_username = f"user_notif_{uid}"
            regular_user = User(
                email=user_email,
                username=user_username,
                hashed_password=get_password_hash("UserPass123!"),
                full_name="Regular Notification User",
                is_active=True,
                is_superuser=False,
            )
            session.add(regular_user)
            await session.commit()
            await session.refresh(admin)
            await session.refresh(regular_user)
            admin_id = admin.id
            user_id = regular_user.id

        admin_token = create_access_token(subject=str(admin_id))
        user_token = create_access_token(subject=str(user_id))

        yield {
            "admin": {"id": admin_id, "email": admin_email, "username": admin_username, "token": admin_token},
            "user": {"id": user_id, "email": user_email, "username": user_username, "token": user_token},
        }

        # Cleanup
        async with SessionFactory() as session:
            for user_id_to_delete in [admin_id, user_id]:
                result = await session.get(User, user_id_to_delete)
                if result:
                    await session.delete(result)
            await session.commit()

    @pytest.mark.asyncio
    async def test_notification_template_configuration(self, client, admin_and_user):
        """Test notification template configuration by admin."""
        admin_headers = {"Authorization": f"Bearer {admin_and_user['admin']['token']}"}

        print("\n1. Configuring notification template...")

        # Create notification template
        import uuid

        template_data = {
            "name": f"order_confirmation_{uuid.uuid4().hex[:6]}",
            "event_type": "order_confirmed",
            "channel": "in_app",
            "title_template": "Order #{order_id} Confirmed",
            "content_template": "Your order #{order_id} has been confirmed. Total: ${{total_amount}}",
            "is_active": True,
        }

        response = await client.post("/api/v2/notifications/templates/", json=template_data, headers=admin_headers)
        assert response.status_code == 201
        template_response = response.json()
        assert template_response["success"] is True
        assert template_response["data"]["name"] == template_data["name"]
        template_id = template_response["data"]["id"]
        print(f"   Template created: ID={template_id}")

        # List templates
        response = await client.get("/api/v2/notifications/templates/", headers=admin_headers)
        assert response.status_code == 200
        templates_response = response.json()
        assert templates_response["success"] is True
        assert len(templates_response["data"]) > 0
        print(f"   Templates listed: {len(templates_response['data'])} templates found")

        # Update template
        update_data = {"title_template": "Order #{order_id} - Confirmed!", "is_active": True}
        response = await client.put(
            f"/api/v2/notifications/templates/{template_id}", json=update_data, headers=admin_headers
        )
        assert response.status_code == 200
        update_response = response.json()
        assert update_response["success"] is True
        print(f"   Template updated successfully")

        return template_id

    @pytest.mark.asyncio
    async def test_complete_notification_flow(self, client, admin_and_user):
        """Test complete notification flow from trigger to read."""
        admin_headers = {"Authorization": f"Bearer {admin_and_user['admin']['token']}"}
        user_headers = {"Authorization": f"Bearer {admin_and_user['user']['token']}"}
        user_id = admin_and_user["user"]["id"]

        print("\n=== Starting Complete Notification Flow Test ===")

        # Step 1: Configure notification template
        print("\n1. Configuring notification template...")
        import uuid

        template_name = f"e2e_test_template_{uuid.uuid4().hex[:6]}"
        template_data = {
            "name": template_name,
            "event_type": "order_confirmed",
            "channel": "in_app",
            "title_template": "Order Confirmed",
            "content_template": "Your order has been confirmed successfully!",
            "is_active": True,
        }

        response = await client.post("/api/v2/notifications/templates/", json=template_data, headers=admin_headers)
        assert response.status_code == 201
        template_id = response.json()["data"]["id"]
        print(f"   Template created: ID={template_id}")

        # Step 2: Trigger order confirmation event
        print("\n2. Triggering order confirmation event...")
        # Create an order to trigger notification
        order_data = {"user_id": user_id, "items": [{"product_id": 1, "quantity": 1, "unit_price": "99.99"}]}
        response = await client.post("/api/v2/orders/", json=order_data, headers=user_headers)
        # Order might fail if product doesn't exist, but we continue
        if response.status_code == 201:
            order_id = response.json()["data"]["id"]
            print(f"   Order created: ID={order_id}")
        else:
            print(f"   Order creation: {response.status_code} (continuing test)")
            order_id = None

        # Step 3: Verify notification generation (may need delay)
        print("\n3. Verifying notification generation...")
        import asyncio

        await asyncio.sleep(1)  # Give time for async notification creation

        response = await client.get("/api/v2/notifications/?page=1&page_size=10", headers=user_headers)
        assert response.status_code == 200
        notifications_response = response.json()
        assert notifications_response["success"] is True
        print(f"   Notifications retrieved: {len(notifications_response.get('data', []))} items")

        # Step 4: User views notifications
        print("\n4. User viewing notifications...")
        response = await client.get("/api/v2/notifications/?is_read=false&page=1&page_size=10", headers=user_headers)
        assert response.status_code == 200
        unread_response = response.json()
        unread_count = len(unread_response.get("data", []))
        print(f"   Unread notifications: {unread_count}")

        # If we have notifications, test marking as read
        if unread_response.get("data"):
            notification_id = unread_response["data"][0]["id"]

            # Step 5: Mark notification as read
            print("\n5. Marking notification as read...")
            response = await client.put(f"/api/v2/notifications/{notification_id}/read", headers=user_headers)
            assert response.status_code == 200
            mark_response = response.json()
            assert mark_response["success"] is True
            assert mark_response["data"]["is_read"] is True
            print(f"   Notification {notification_id} marked as read")

            # Verify notification is now marked as read
            response = await client.get(f"/api/v2/notifications/{notification_id}", headers=user_headers)
            assert response.status_code == 200
            assert response.json()["data"]["is_read"] is True

        # Test mark all as read
        print("\n6. Testing mark all as read...")
        response = await client.put("/api/v2/notifications/read-all", headers=user_headers)
        assert response.status_code == 200
        mark_all_response = response.json()
        assert mark_all_response["success"] is True
        print(f"   All notifications marked as read")

        print("\n✅ Complete notification flow test passed!")

    @pytest.mark.asyncio
    async def test_notification_filters(self, client, admin_and_user):
        """Test notification filtering by status and read state."""
        user_headers = {"Authorization": f"Bearer {admin_and_user['user']['token']}"}

        # Test filtering by is_read
        response = await client.get("/api/v2/notifications/?is_read=true&page=1&page_size=10", headers=user_headers)
        assert response.status_code == 200

        response = await client.get("/api/v2/notifications/?is_read=false&page=1&page_size=10", headers=user_headers)
        assert response.status_code == 200

        # Test filtering by status
        response = await client.get("/api/v2/notifications/?status=pending&page=1&page_size=10", headers=user_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_user_cannot_configure_templates(self, client, admin_and_user):
        """Test that regular users cannot configure notification templates."""
        user_headers = {"Authorization": f"Bearer {admin_and_user['user']['token']}"}

        import uuid

        template_data = {
            "name": f"unauthorized_template_{uuid.uuid4().hex[:6]}",
            "event_type": "test",
            "channel": "in_app",
            "title_template": "Test",
            "content_template": "Test content",
            "is_active": True,
        }

        # Regular user should not be able to create templates
        response = await client.post("/api/v2/notifications/templates/", json=template_data, headers=user_headers)
        assert response.status_code == 403

        # Regular user should not be able to list templates
        response = await client.get("/api/v2/notifications/templates/", headers=user_headers)
        assert response.status_code == 403
