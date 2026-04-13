"""
Edge cases and boundary condition tests for products module.

Tests cover:
- Empty/null name handling
- Long description boundaries
- Negative price validation
- Duplicate SKU handling
- Concurrent updates
- Category edge cases
"""

import asyncio
from decimal import Decimal

import pytest
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.products.models import Product
from app.modules.products.schemas import ProductCreate, ProductUpdate
from tests.conftest import NONEXISTENT_ID


@pytest.mark.asyncio
class TestProductNameEdgeCases:
    """Tests for product name boundary conditions."""

    async def test_product_empty_name(self, client, superuser_headers):
        """Test product with empty name."""
        response = await client.post(
            "/api/v1/products",
            json={
                "name": "",
                "sku": "EMPTY-001",
                "price": "99.99",
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_product_whitespace_only_name(self, client, superuser_headers):
        """Test product with whitespace-only name."""
        response = await client.post(
            "/api/v1/products",
            json={
                "name": "   ",
                "sku": "SPACE-001",
                "price": "99.99",
            },
            headers=superuser_headers,
        )
        # Should be rejected due to min_length=1
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_product_null_name(self, client, superuser_headers):
        """Test product with null name."""
        response = await client.post(
            "/api/v1/products",
            json={
                "name": None,
                "sku": "NULL-001",
                "price": "99.99",
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_product_name_maximum_length(self, client, superuser_headers):
        """Test product name at maximum length (200 chars)."""
        long_name = "A" * 200
        response = await client.post(
            "/api/v1/products",
            json={
                "name": long_name,
                "sku": "MAXNAME-001",
                "price": "99.99",
            },
            headers=superuser_headers,
        )
        # Should succeed at exactly 200 chars
        assert response.status_code == status.HTTP_201_CREATED

    async def test_product_name_exceeds_maximum(self, client, superuser_headers):
        """Test product name exceeding maximum length (201+ chars)."""
        too_long_name = "A" * 201
        response = await client.post(
            "/api/v1/products",
            json={
                "name": too_long_name,
                "sku": "TOOLONG-001",
                "price": "99.99",
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_product_name_single_character(self, client, superuser_headers):
        """Test product name with single character (minimum)."""
        response = await client.post(
            "/api/v1/products",
            json={
                "name": "X",
                "sku": "SINGLE-001",
                "price": "99.99",
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED

    async def test_product_name_special_characters(self, client, superuser_headers):
        """Test product name with special characters."""
        import uuid

        special_names = [
            "Product with <script>alert('xss')</script>",
            "Product with 'quotes' and \"double quotes\"",
            "Product with emoji 🔥🚀💯",
            "日本語製品名",
            "Product\nwith\nnewlines",
            "Product\twith\ttabs",
        ]

        for name in special_names:
            response = await client.post(
                "/api/v1/products",
                json={
                    "name": name,
                    "sku": f"SPEC-{uuid.uuid4().hex[:8]}",
                    "price": "99.99",
                },
                headers=superuser_headers,
            )
            # Should either succeed or get validation error, not crash
            assert response.status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_422_UNPROCESSABLE_CONTENT,
            ]


@pytest.mark.asyncio
class TestProductDescriptionEdgeCases:
    """Tests for product description boundary conditions."""

    async def test_product_empty_description(self, client, superuser_headers):
        """Test product with empty description."""
        import uuid

        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Product with empty desc",
                "sku": f"EMPTYDESC-{uuid.uuid4().hex[:8]}",
                "description": "",
                "price": "99.99",
            },
            headers=superuser_headers,
        )
        # Empty string should be accepted (optional field)
        assert response.status_code == status.HTTP_201_CREATED

    async def test_product_null_description(self, client, superuser_headers):
        """Test product with null description."""
        import uuid

        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Product with null desc",
                "sku": f"NULLDESC-{uuid.uuid4().hex[:8]}",
                "description": None,
                "price": "99.99",
            },
            headers=superuser_headers,
        )
        # Null should be accepted (optional field)
        assert response.status_code == status.HTTP_201_CREATED

    async def test_product_description_maximum_length(self, client, superuser_headers):
        """Test product description at maximum length (1000 chars)."""
        import uuid

        long_desc = "D" * 1000
        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Product with max desc",
                "sku": f"MAXDESC-{uuid.uuid4().hex[:8]}",
                "description": long_desc,
                "price": "99.99",
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED

    async def test_product_description_exceeds_maximum(self, client, superuser_headers):
        """Test product description exceeding maximum length."""
        import uuid

        too_long_desc = "D" * 1001
        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Product with too long desc",
                "sku": f"TOOLONGDESC-{uuid.uuid4().hex[:8]}",
                "description": too_long_desc,
                "price": "99.99",
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_product_description_html_content(self, client, superuser_headers):
        """Test product description with HTML content."""
        import uuid

        html_desc = "<h1>Title</h1><p>Paragraph</p><script>alert('xss')</script>"
        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Product with HTML desc",
                "sku": f"HTMLDESC-{uuid.uuid4().hex[:8]}",
                "description": html_desc,
                "price": "99.99",
            },
            headers=superuser_headers,
        )
        # HTML should be accepted as plain text
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.asyncio
class TestProductPriceEdgeCases:
    """Tests for product price boundary conditions."""

    async def test_product_zero_price(self, client, superuser_headers):
        """Test product with zero price."""
        import uuid

        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Free Product",
                "sku": f"FREE-{uuid.uuid4().hex[:8]}",
                "price": "0.00",
            },
            headers=superuser_headers,
        )
        # Should fail validation (gt=0 means greater than 0)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_product_negative_price(self, client, superuser_headers):
        """Test product with negative price."""
        import uuid

        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Negative Price Product",
                "sku": f"NEG-{uuid.uuid4().hex[:8]}",
                "price": "-10.00",
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_product_minimum_positive_price(self, client, superuser_headers):
        """Test product with minimum positive price."""
        import uuid

        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Minimum Price Product",
                "sku": f"MIN-{uuid.uuid4().hex[:8]}",
                "price": "0.01",
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED

    async def test_product_very_small_price(self, client, superuser_headers):
        """Test product with very small price."""
        import uuid

        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Very Cheap Product",
                "sku": f"CHEAP-{uuid.uuid4().hex[:8]}",
                "price": "0.001",
            },
            headers=superuser_headers,
        )
        # Very small prices should be handled
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ]

    async def test_product_very_large_price(self, client, superuser_headers):
        """Test product with very large price."""
        import uuid

        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Expensive Product",
                "sku": f"EXP-{uuid.uuid4().hex[:8]}",
                "price": "999999999999.99",
            },
            headers=superuser_headers,
        )
        # Large prices should be handled by Decimal
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            status.HTTP_400_BAD_REQUEST,
        ]

    async def test_product_many_decimal_places(self, client, superuser_headers):
        """Test product price with many decimal places."""
        import uuid

        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Precise Price Product",
                "sku": f"PREC-{uuid.uuid4().hex[:8]}",
                "price": "99.999999",
            },
            headers=superuser_headers,
        )
        # Many decimal places might be truncated or rejected
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ]

    async def test_product_null_price(self, client, superuser_headers):
        """Test product with null price."""
        import uuid

        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Null Price Product",
                "sku": f"NULLP-{uuid.uuid4().hex[:8]}",
                "price": None,
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_product_string_price(self, client, superuser_headers):
        """Test product with string price instead of number."""
        import uuid

        response = await client.post(
            "/api/v1/products",
            json={
                "name": "String Price Product",
                "sku": f"STRP-{uuid.uuid4().hex[:8]}",
                "price": "not-a-number",
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
class TestProductSKUEdgeCases:
    """Tests for product SKU boundary conditions."""

    async def test_product_empty_sku(self, client, superuser_headers):
        """Test product with empty SKU."""
        import uuid

        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Product with empty SKU",
                "sku": "",
                "price": "99.99",
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_product_null_sku(self, client, superuser_headers):
        """Test product with null SKU."""
        import uuid

        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Product with null SKU",
                "sku": None,
                "price": "99.99",
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_product_duplicate_sku(self, client, superuser_headers):
        """Test creating product with duplicate SKU."""
        import uuid

        sku = f"DUPLICATE-{uuid.uuid4().hex[:8]}"

        # Create first product
        response1 = await client.post(
            "/api/v1/products",
            json={
                "name": "First Product",
                "sku": sku,
                "price": "99.99",
            },
            headers=superuser_headers,
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Try to create second with same SKU
        response2 = await client.post(
            "/api/v1/products",
            json={
                "name": "Second Product",
                "sku": sku,
                "price": "49.99",
            },
            headers=superuser_headers,
        )
        assert response2.status_code == status.HTTP_409_CONFLICT

    async def test_product_sku_maximum_length(self, client, superuser_headers):
        """Test product SKU at maximum length (50 chars)."""
        import uuid

        long_sku = "SKU-" + "A" * 46  # Total 50 chars
        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Product with long SKU",
                "sku": long_sku,
                "price": "99.99",
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED

    async def test_product_sku_exceeds_maximum(self, client, superuser_headers):
        """Test product SKU exceeding maximum length."""
        import uuid

        too_long_sku = "SKU-" + "A" * 47  # Total 51 chars
        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Product with too long SKU",
                "sku": too_long_sku,
                "price": "99.99",
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_product_sku_case_sensitivity(self, client, superuser_headers):
        """Test SKU case sensitivity (should be unique case-insensitive)."""
        import uuid

        sku = f"CASE-{uuid.uuid4().hex[:8]}"

        # Create with uppercase
        response1 = await client.post(
            "/api/v1/products",
            json={
                "name": "Uppercase SKU Product",
                "sku": sku.upper(),
                "price": "99.99",
            },
            headers=superuser_headers,
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Try with lowercase - may succeed or fail depending on DB collation
        response2 = await client.post(
            "/api/v1/products",
            json={
                "name": "Lowercase SKU Product",
                "sku": sku.lower(),
                "price": "49.99",
            },
            headers=superuser_headers,
        )
        assert response2.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_409_CONFLICT,
        ]

    async def test_product_sku_with_special_characters(self, client, superuser_headers):
        """Test product SKU with special characters."""
        import uuid

        special_skus = [
            f"SKU-{uuid.uuid4().hex[:8]}-with-dash",
            f"SKU_{uuid.uuid4().hex[:8]}_with_underscore",
            f"SKU.{uuid.uuid4().hex[:8]}.with.dots",
            f"SKU/{uuid.uuid4().hex[:8]}/with/slashes",
            f"SKU:{uuid.uuid4().hex[:8]}:with:colons",
        ]

        for sku in special_skus:
            response = await client.post(
                "/api/v1/products",
                json={
                    "name": f"Product with special SKU {sku}",
                    "sku": sku,
                    "price": "99.99",
                },
                headers=superuser_headers,
            )
            # Should either succeed or get validation error
            assert response.status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_422_UNPROCESSABLE_CONTENT,
            ]


@pytest.mark.asyncio
class TestProductCategoryEdgeCases:
    """Tests for product category boundary conditions."""

    async def test_product_null_category(self, client, superuser_headers):
        """Test product with null category."""
        import uuid

        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Product without category",
                "sku": f"NOCAT-{uuid.uuid4().hex[:8]}",
                "price": "99.99",
                "category": None,
            },
            headers=superuser_headers,
        )
        # Null should be accepted (optional field)
        assert response.status_code == status.HTTP_201_CREATED

    async def test_product_empty_category(self, client, superuser_headers):
        """Test product with empty category."""
        import uuid

        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Product with empty category",
                "sku": f"EMPTYCAT-{uuid.uuid4().hex[:8]}",
                "price": "99.99",
                "category": "",
            },
            headers=superuser_headers,
        )
        # Empty should be accepted
        assert response.status_code == status.HTTP_201_CREATED

    async def test_product_category_maximum_length(self, client, superuser_headers):
        """Test product category at maximum length (100 chars)."""
        import uuid

        long_category = "C" * 100
        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Product with long category",
                "sku": f"LONGCAT-{uuid.uuid4().hex[:8]}",
                "price": "99.99",
                "category": long_category,
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED

    async def test_product_category_exceeds_maximum(self, client, superuser_headers):
        """Test product category exceeding maximum length."""
        import uuid

        too_long_category = "C" * 101
        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Product with too long category",
                "sku": f"TOOLONGCAT-{uuid.uuid4().hex[:8]}",
                "price": "99.99",
                "category": too_long_category,
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
class TestProductConcurrentOperations:
    """Tests for concurrent product operations."""

    async def test_concurrent_create_same_sku(self, client, superuser_headers):
        """Test concurrent creation with same SKU."""
        import uuid

        sku = f"CONCURRENT-{uuid.uuid4().hex[:8]}"

        async def create_product():
            return await client.post(
                "/api/v1/products",
                json={
                    "name": "Concurrent Product",
                    "sku": sku,
                    "price": "99.99",
                },
                headers=superuser_headers,
            )

        # Launch multiple concurrent requests
        tasks = [create_product() for _ in range(5)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and failures
        success_count = sum(1 for r in responses if isinstance(r, type(await client.get("/"))) and r.status_code == 201)
        conflict_count = sum(
            1 for r in responses if isinstance(r, type(await client.get("/"))) and r.status_code == 409
        )

        # Only one should succeed
        assert success_count == 1
        assert conflict_count == 4

    async def test_concurrent_update_same_product(self, session: AsyncSession, test_product):
        """Test concurrent updates on same product."""
        from app.modules.products import service as product_service

        async def update_product(suffix):
            return await product_service.update_product(
                session,
                test_product.id,
                ProductUpdate(name=f"Updated {suffix}"),
            )

        # Launch concurrent updates
        tasks = [update_product(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Some should succeed, handle exceptions
        successful_updates = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_updates) >= 1


@pytest.mark.asyncio
class TestProductIsActiveEdgeCases:
    """Tests for product is_active field edge cases."""

    async def test_product_is_active_true(self, client, superuser_headers):
        """Test product with is_active=true."""
        import uuid

        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Active Product",
                "sku": f"ACTIVE-{uuid.uuid4().hex[:8]}",
                "price": "99.99",
                "is_active": True,
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["data"]["is_active"] is True

    async def test_product_is_active_false(self, client, superuser_headers):
        """Test product with is_active=false."""
        import uuid

        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Inactive Product",
                "sku": f"INACTIVE-{uuid.uuid4().hex[:8]}",
                "price": "99.99",
                "is_active": False,
            },
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["data"]["is_active"] is False

    async def test_product_is_active_null(self, client, superuser_headers):
        """Test product with is_active=null."""
        import uuid

        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Null Active Product",
                "sku": f"NULLACT-{uuid.uuid4().hex[:8]}",
                "price": "99.99",
                "is_active": None,
            },
            headers=superuser_headers,
        )
        # Should use default value (True)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["data"]["is_active"] is True

    async def test_product_is_active_missing(self, client, superuser_headers):
        """Test product without is_active field."""
        import uuid

        response = await client.post(
            "/api/v1/products",
            json={
                "name": "No Active Field Product",
                "sku": f"NOACT-{uuid.uuid4().hex[:8]}",
                "price": "99.99",
            },
            headers=superuser_headers,
        )
        # Should use default value (True)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["data"]["is_active"] is True


@pytest.mark.asyncio
class TestProductNonExistentOperations:
    """Tests for operations on non-existent products."""

    async def test_get_nonexistent_product(self, client, superuser_headers):
        """Test getting a product that doesn't exist."""
        response = await client.get(
            f"/api/v1/products/{NONEXISTENT_ID}",
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_nonexistent_product(self, client, superuser_headers):
        """Test updating a product that doesn't exist."""
        response = await client.put(
            f"/api/v1/products/{NONEXISTENT_ID}",
            json={"name": "Updated Name"},
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_nonexistent_product(self, client, superuser_headers):
        """Test deleting a product that doesn't exist."""
        response = await client.delete(
            f"/api/v1/products/{NONEXISTENT_ID}",
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_product_with_null_data(self, client, test_product, superuser_headers):
        """Test updating product with null data."""
        response = await client.put(
            f"/api/v1/products/{test_product.id}",
            json={},
            headers=superuser_headers,
        )
        # Empty update should succeed (no changes)
        assert response.status_code == status.HTTP_200_OK

    async def test_update_product_partial_data(self, client, test_product, superuser_headers):
        """Test updating product with partial data."""
        response = await client.put(
            f"/api/v1/products/{test_product.id}",
            json={"price": "199.99"},  # Only update price
            headers=superuser_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["price"] == "199.99"
        # Other fields should remain unchanged
        assert data["name"] == test_product.name
